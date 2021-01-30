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
__version__ = '0.7.1.3'

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
import logging.handlers
import re
import os
import paho.mqtt.client as mqtt
import socket
import ssl
import sys
import threading
import time
import typing
from urllib.parse import parse_qs, urlparse, ParseResult
import _thread

import pima


class AlarmServer(threading.Thread):
  """Class maintaining the current status and sends commands to the alarm."""

  _SERIAL_BASE = '/dev/serial/by-path'

  def __init__(self) -> None:
    self._alarm: pima.Alarm = None
    ipaddr: str = None
    ipport: int = None
    serialport: str = None
    if _parsed_args.pima_host and _parsed_args.pima_port:
      # Connected by ethernet
      ipaddr = _parsed_args.pima_host
      ipport = _parsed_args.pima_port
      logging.debug('IP Address: %s:%d.', ipaddr, ipport)
    elif _parsed_args.serialport:
      # Connected by Serial
      serialport = _parsed_args.serialport
      logging.debug('Port: %s.', serialport)
    else:
      # Connected by serial port
      try:
        ports = os.listdir(self._SERIAL_BASE)  # type: typing.List[str]
      except IOError:
        logging.exception('Failed to lookup serial port.')
        sys.exit(1)
      if not ports:
        logging.error('Serial port is missing!')
        sys.exit(1)
      serialport = os.path.join(self._SERIAL_BASE, ports[0])
      logging.debug('Port: %s.', serialport)
    self._alarm_args = _parsed_args.zones, serialport, ipaddr, ipport  # type: tuple
    try:
      self._create_alarm()
    except pima.Error:
      logging.exception('Failed to create alarm object.')
      sys.exit(1)
    self._status_lock = threading.Lock()
    self._alarm_lock = threading.Lock()
    super(AlarmServer, self).__init__(name='PIMA Alarm Server')

  def __del__(self) -> None:
    if self._alarm:
      del self._alarm

  def run(self) -> None:
    """Continuously query the alarm for status."""
    while True:
      try:
        with self._alarm_lock:
          status = self._alarm.get_status()  # type: pima.Status
          while not status['logged in']:
            # Re-login if previous session ended.
            status = self._alarm.login(_parsed_args.login)
          self._set_status(status)
        time.sleep(1)
      except:
        logging.exception('Exception raised by Alarm.')
        try:
          with self._alarm_lock:
            logging.info('Trying to create the Alarm anew.')
            self._create_alarm()
        except pima.Error:
          logging.exception('Failed to recreate Alarm object. Exit for a clean restart.')
          _thread.interrupt_main()

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

  def _create_alarm(self) -> None:
    self._alarm = pima.Alarm(*self._alarm_args)  # type: pima.Alarm
    self._status = self._alarm.get_status()  # type: pima.Status
    logging.info('Status: %s.', self._status)
    while not self._status['logged in']:
      self._status = self._alarm.login(_parsed_args.login)
      logging.info('Status: %s.', self._status)


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
    partitions = pima.Partitions({int(p) for p in query.get('partitions', ['1'])})
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


def from_json(data: bytes) -> dict:
  """Encode the provided dictionary as JSON."""
  return json.loads(data.decode('utf-8'))


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
    if query.get('key', [''])[0] != _parsed_args.key:
      return False
    return True


def mqtt_on_connect(client: mqtt.Client, userdata, flags, rc):
  logging.debug('Connected to MQTT at %s:%d', _parsed_args.mqtt_host, _parsed_args.mqtt_port)

  mqtt_publish_discovery()
  mqtt_publish_lwt_online()

  client.subscribe(_mqtt_topics['sub'])

  logging.debug('Completed registration to MQTT')


def mqtt_on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
  try:
    mqtt_publish_status(RunJsonCommand(from_json(message.payload)))
  except pima.Error:
    logging.exception('Failed handling MQTT message')


def mqtt_on_disconnect(client: mqtt.Client, userdata, rc):
  logging.info('Disconnected from MQTT: %d', rc)
  mqtt_connect()


def mqtt_publish_status(status: dict) -> None:
  if _mqtt_client:
    _mqtt_client.publish(_mqtt_topics['pub'], payload=to_json(status))


def mqtt_publish_discovery() -> None:
  if _mqtt_client:
    device_info = {
        'identifiers': [f'pima_alarm'],
        'manufacturer': f'PIMA',
        'model': f'Hunter Pro 8{_parsed_args.zones}',
        'name': 'PIMA Alarm',
    }
    alarm_config = {
        'name':
            'PIMA Alarm',
        'unique_id':
            'pima_alarm',
        'device':
            device_info,
        'state_topic':
            _mqtt_topics['pub'],
        'command_topic':
            _mqtt_topics['sub'],
        'availability_topic':
            _mqtt_topics['lwt'],
        'code_arm_required':
            False,
        'code_disarm_required':
            False,
        'value_template':
            """{% if value_json['partitions']['1'] == 'home1' %}armed_home{%
                              elif value_json['partitions']['1'] == 'full_arm' %}armed_away{%
                              else %}disarmed{% endif %}""",
        'payload_disarm':
            '{"command": "arm", "mode": "disarm"}',
        'payload_arm_home':
            '{"command": "arm", "mode": "home1"}',
        'payload_arm_away':
            '{"command": "arm", "mode": "full_arm"}'
    }
    _mqtt_client.publish(_mqtt_topics['discovery'].format('alarm_control_panel'),
                         payload=to_json(alarm_config),
                         retain=True)
    for i in range(1, min(_parsed_args.mqtt_discovery_max_zone, _parsed_args.zones) + 1):
      open_zones_config = {
          'name':
              f'Alarm Zone {i} Open',
          'unique_id':
              f'pima_alarm_zone_{i}_open',
          'device': {
              **device_info, 'via_device': 'pima_alarm'
          },
          'state_topic':
              _mqtt_topics['pub'],
          'availability_topic':
              _mqtt_topics['lwt'],
          'payload_on':
              'on',
          'payload_off':
              'off',
          'value_template':
              f"{{% if {i} in value_json['open zones'] %}}on{{% else %}}off{{% endif %}}"
      }
      alarmed_zones_config = {
          'name':
              f'Alarm Zone {i} Alarming',
          'unique_id':
              f'pima_alarm_zone_{i}_alarming',
          'device': {
              **device_info, 'via_device': 'pima_alarm'
          },
          'state_topic':
              _mqtt_topics['pub'],
          'availability_topic':
              _mqtt_topics['lwt'],
          'payload_on':
              'on',
          'payload_off':
              'off',
          'value_template':
              f"{{% if {i} in value_json['alarmed zones'] %}}on{{% else %}}off{{% endif %}}"
      }
      _mqtt_client.publish(_mqtt_topics['discovery'].format(f'binary_sensor/open_zone_{i}'),
                           payload=to_json(open_zones_config),
                           retain=True)
      _mqtt_client.publish(_mqtt_topics['discovery'].format(f'binary_sensor/alarmed_zone_{i}'),
                           payload=to_json(alarmed_zones_config),
                           retain=True)


def mqtt_publish_lwt_online() -> None:
  if _mqtt_client:
    logging.debug('Publishing online to LWT')
    _mqtt_client.publish(_mqtt_topics['lwt'], payload='online', retain=True)


def mqtt_connect() -> None:
  if not _mqtt_client:
    return

  logging.debug('Connecting to MQTT at %s:%d', _parsed_args.mqtt_host, _parsed_args.mqtt_port)

  _mqtt_client.will_set(_mqtt_topics['lwt'], payload='offline', retain=True)

  while True:
    try:
      _mqtt_client.connect(_parsed_args.mqtt_host, _parsed_args.mqtt_port)
    except (socket.timeout, OSError):
      logging.exception('Failed to connect to MQTT broker. Retrying in 5 seconds...')
      time.sleep(5)
    else:
      break


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
  arg_parser = argparse.ArgumentParser(description='JSON server for PIMA alarms.',
                                       allow_abbrev=False)
  arg_parser.add_argument('--ssl_cert', help='Path to SSL certificate file.')
  arg_parser.add_argument('--ssl_key', default=None, help='Path to SSL key file.')
  arg_parser.add_argument('-p', '--port', required=True, type=int, help='Port for the server.')
  arg_parser.add_argument('-k', '--key', required=True, help='URL key to authenticate calls.')
  arg_parser.add_argument('-l',
                          '--login',
                          required=True,
                          choices=LoginCodes(),
                          help='Login code to the PIMA alarm.')
  arg_parser.add_argument('-z',
                          '--zones',
                          type=int,
                          default=32,
                          choices={32, 96, 144},
                          help='Alarm supported zones.')
  arg_parser.add_argument(
      '--serialport',
      default=None,
      help='Serial port, e.g. /dev/serial0. Needed if connected directly through GPIO serial.')
  arg_parser.add_argument('--pima_host',
                          default=None,
                          help='Pima alarm hostname or IP address. if connected by ethernet.')
  arg_parser.add_argument('--pima_port',
                          type=int,
                          default=None,
                          help='Pima alarm port. if connected by ethernet.')
  arg_parser.add_argument('--mqtt_host', default=None, help='MQTT broker hostname or IP address.')
  arg_parser.add_argument('--mqtt_port', type=int, default=1883, help='MQTT broker port.')
  arg_parser.add_argument('--mqtt_client_id', default=None, help='MQTT client ID.')
  arg_parser.add_argument('--mqtt_user', default=None, help='<user:password> for the MQTT channel.')
  arg_parser.add_argument('--mqtt_topic', default='pima_alarm', help='MQTT topic.')
  arg_parser.add_argument('--mqtt_discovery_prefix',
                          default='homeassistant',
                          help='MQTT discovery prefix for HomeAssistant.')
  arg_parser.add_argument('--mqtt_discovery_max_zone',
                          default=8,
                          type=int,
                          help='The highest number to enable for MQTT discovery ' +
                          '(to avoid adding sensors for inoperative zones).')
  arg_parser.add_argument('--log_level',
                          default='WARNING',
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
                        datefmt='%m%d %H:%M:%S',
                        style='{'))
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
    _mqtt_topics['lwt'] = os.path.join(_parsed_args.mqtt_topic, 'LWT')
    _mqtt_topics['discovery'] = os.path.join(_parsed_args.mqtt_discovery_prefix, '{}', 'pima_alarm',
                                             'config')
    _mqtt_client = mqtt.Client(client_id=_parsed_args.mqtt_client_id, clean_session=True)
    _mqtt_client.on_connect = mqtt_on_connect
    _mqtt_client.on_message = mqtt_on_message
    _mqtt_client.on_disconnect = mqtt_on_disconnect
    if _parsed_args.mqtt_user:
      _mqtt_client.username_pw_set(*_parsed_args.mqtt_user.split(':', 1))
    mqtt_connect()
    _mqtt_client.loop_start()

  httpd = HTTPServer(('', _parsed_args.port), HTTPRequestHandler)
  if _parsed_args.ssl_cert:
    httpd.socket = ssl.wrap_socket(httpd.socket,
                                   certfile=_parsed_args.ssl_cert,
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
