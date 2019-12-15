#!/usr/bin/env python3
"""
JSON server module for PIMA alarms.
Uses pima.py to connect and control the alarm.

PIMA is a trademark of PIMA Electronic Systems Ltd, http://www.pima-alarms.com.
This module was built with no affiliation of PIMA Electronic Systems Ltd.

Copyright © 2019 Dror Eiger <droreiger@gmail.com>

This module is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This module is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

__author__ = 'droreiger@gmail.com (Dror Eiger)'

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
import logging.handlers
import re
import os
import paho.mqtt.client as mqtt
import ssl
import sys
import threading
import time
import typing
from urllib.parse import parse_qs, urlparse, ParseResult

import pima


class AlarmServer(threading.Thread):
  """Class maintaining the current status and sends commands to the alarm."""
  _SERIAL_BASE = '/dev/serial/by-path'
  def __init__(self) -> None:
    try:
      ports = os.listdir(self._SERIAL_BASE)  # type: typing.List[str]
    except IOError:
      logging.exception('Failed to lookup serial port.')
      sys.exit(1)
    if not ports:
      logging.error('Serial port is missing!')
      sys.exit(1)
    port = os.path.join(self._SERIAL_BASE, ports[0])  # type: str
    logging.debug('Port: %s.', port)
    try:
      self._alarm = pima.Alarm(_parsed_args.zones, port)  # type: pima.Alarm
    except pima.Error:
      logging.exception('Failed to create alarm class.')
      sys.exit(1)
    self._status = self._alarm.get_status()  # type: pima.Status
    logging.info('Status: %s.', self._status)
    while not self._status['logged in']:
      self._status = self._alarm.login(_parsed_args.login)
      logging.info('Status: %s.', self._status)
    self._status_lock = threading.Lock()
    self._alarm_lock = threading.Lock()
    super(AlarmServer, self).__init__(name='PIMA Alarm Server')

  def __del__(self) -> None:
    if self._alarm:
      del self._alarm

  def run(self) -> None:
    """Continuously query the alarm for status."""
    while True:
      with self._alarm_lock:
        status = self._alarm.get_status()  # type: pima.Status
        while not status['logged in']:
          # Re-login if previous session ended.
          status = self._alarm.login(_parsed_args.login)
        self._set_status(status)
      time.sleep(1)

  def get_status(self) -> pima.Status:
    """Gets the internally stored alarm status."""
    with self._status_lock:
      return self._status

  def arm(self, mode: pima.Arm, partitions: pima.Partitions) -> pima.Status:
    """Arms (or disarms) the alarm, returning the status."""
    with self._alarm_lock:
      status = self._alarm.arm(mode, partitions)  # type: pima.Status
      self._set_status(status)
      return status

  def _set_status(self, status: pima.Status) -> None:
    with self._status_lock:
      if self._status == status:
        return  # No update, ignore.
      self._status = status
    logging.info('Status: %s.', self._status)
    mqtt_publish_status(status)


def RunJsonCommand(query: dict) -> dict:
  _CMD_STATUS = 'status'
  _CMD_ARM = 'arm'
  if not _pima_server:
    return {'error': 'No server.'}
  try:
    command = query['command']
  except KeyError:
    return {'error': 'Missing command.'}
  if isinstance(command, list):
    command = command[0]
  if command == _CMD_STATUS:
    return _pima_server.get_status()
  if command == _CMD_ARM:
    try:
      mode = query['mode']
      if isinstance(mode, list):
        mode = mode[0]
      mode = pima.Arm[mode.upper()]
    except KeyError:
      return {'error': 'Invalid arm mode.'}
    partitions = pima.Partitions(
        {int(p) for p in query.get('partitions', ['1'])})
    return _pima_server.arm(mode, partitions)
  return {'error': 'Invalid command.'}


class JsonEncoder(json.JSONEncoder):
  """Class for JSON encoding."""
  def default(self, obj):
    if isinstance(obj, set):
      return list(obj)
    return json.JSONEncoder.default(self, obj)


def to_json(data: dict) -> bytes:
  """Encode the provided dictionary as JSON."""
  return bytes(json.dumps(data, cls=JsonEncoder), 'utf-8')


class HTTPRequestHandler(BaseHTTPRequestHandler):
  """Handler for PIMA alarm http requests."""
  _PIMA_URL = '/pima'

  def do_HEAD(self) -> None:
    """Return a JSON header."""
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()

  def do_GET(self) -> None:
    """Vaildate and run the request."""
    self.do_HEAD()
    logging.debug('Request: %s', self.path)
    parsed_url = urlparse(self.path)
    query = parse_qs(parsed_url.query)
    if not self.is_valid_url(parsed_url.path, query) or not _pima_server:
      self.write_json({'error': 'Invalid URL.'})
      return
    try:
      self.write_json(RunJsonCommand(query))
    except pima.Error:
      logging.exception('Failed to run command.')
      self.write_json({'error': 'Failed to run command.'})
      sys.exit(1)

  def write_json(self, data: dict) -> None:
    """Send out the provided data dict as JSON."""
    logging.debug('Response: %r', data)
    self.wfile.write(to_json(data))

  @classmethod
  def is_valid_url(cls, path: str, query: dict) -> bool:
    """Validate the provided URL."""
    if path != cls._PIMA_URL:
      return False
    if query.get('key',[''])[0] != _parsed_args.key:
      return False
    return True


def mqtt_on_connect(client: mqtt.Client, userdata, flags, rc):
  client.subscribe(_mqtt_topics['sub'])


def mqtt_on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
  mqtt_publish_status(RunJsonCommand(message.payload))


def mqtt_publish_status(status: dict) -> None:
  if _mqtt_client:
    _mqtt_client.publish(_mqtt_topics['pub'], payload=to_json(status))


class LoginCodes(object):
  """'Container' for all valid login codes."""
  def __contains__(self, value) -> bool:
    if not isinstance(value, str):
      return False
    return bool(re.fullmatch(r'\d{4,6}', value))
  def __iter__(self):
    yield '000000'


def ParseArguments() -> argparse.Namespace:
  """Parse command line arguments."""
  arg_parser = argparse.ArgumentParser(
      description='JSON server for PIMA alarms.',
      allow_abbrev=False)
  arg_parser.add_argument('--ssl_cert',
                          help='Path to SSL certificate file.')
  arg_parser.add_argument('--ssl_key', default=None,
                          help='Path to SSL key file.')
  arg_parser.add_argument('-p', '--port', required=True, type=int,
                          help='Port for the server.')
  arg_parser.add_argument('-k', '--key', required=True,
                          help='URL key to authenticate calls.')
  arg_parser.add_argument('-l', '--login', required=True, choices=LoginCodes(),
                          help='Login code to the PIMA alarm.')
  arg_parser.add_argument('-z', '--zones', type=int, default=32,
                          choices={32, 96, 144}, help='Alarm supported zones.')
  arg_parser.add_argument('--mqtt_host', default=None,
                          help='MQTT broker hostname or IP address.')
  arg_parser.add_argument('--mqtt_port', type=int, default=1883,
                          help='MQTT broker port.')
  arg_parser.add_argument('--mqtt_client_id', default=None,
                          help='MQTT client ID.')
  arg_parser.add_argument('--mqtt_user', default=None,
                          help='<user:password> for the MQTT channel.')
  arg_parser.add_argument('--mqtt_topic', default='pima_alarm',
                          help='MQTT topic.')
  arg_parser.add_argument('--log_level', default='WARNING',
                          choices={'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'},
                          help='Minimal log level.')
  return arg_parser.parse_args()


if __name__ == '__main__':
  _parsed_args = ParseArguments()  # type: argparse.Namespace

  log_socket = '/var/run/syslog' if sys.platform == 'darwin' else '/dev/log'
  logging_handler = logging.handlers.SysLogHandler(address=log_socket)
  logging_handler.setFormatter(
      logging.Formatter(fmt='{levelname[0]}{asctime}.{msecs:03.0f}  '
                        '{filename}:{lineno}] {message}',
                         datefmt='%m%d %H:%M:%S', style='{'))
  logger = logging.getLogger()
  logger.setLevel(_parsed_args.log_level)
  logger.addHandler(logging_handler)

  _pima_server = AlarmServer()  # type: AlarmServer
  _pima_server.start()

  _mqtt_client = None  # type: typing.Optional[mqtt.Client]
  _mqtt_topics = {}  # type: typing.Dict[str, str]
  if _parsed_args.mqtt_host:
    _mqtt_topics['pub'] = os.path.join(_parsed_args.mqtt_topic, 'status')
    _mqtt_topics['sub'] = os.path.join(_parsed_args.mqtt_topic, 'command')
    _mqtt_client = mqtt.Client(client_id=_parsed_args.mqtt_client_id,
                               clean_session=True)
    _mqtt_client.on_connect = mqtt_on_connect
    _mqtt_client.on_message = mqtt_on_message
    if _parsed_args.mqtt_user:
      _mqtt_client.username_pw_set(*_parsed_args.mqtt_user.split(':',1))
    _mqtt_client.connect(_parsed_args.mqtt_host, _parsed_args.mqtt_port)
    _mqtt_client.loop_start()

  httpd = HTTPServer(('', _parsed_args.port), HTTPRequestHandler)
  if _parsed_args.ssl_cert:
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile=_parsed_args.ssl_cert,
                                   keyfile=_parsed_args.ssl_key,
                                   server_side=True)
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    pass

  httpd.server_close()
  if _mqtt_client:
    _mqtt_client.loop_stop()
  del _pima_server
