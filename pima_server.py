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
import re
import os
import ssl
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse, ParseResult

import pima


_pima_server = None
_parsed_args = None


class AlarmServer(threading.Thread):
  """Class maintaining the current status and sends commands to the alarm."""
  _SERIAL_BASE = '/dev/serial/by-path'
  def __init__(self):
    self._alarm = None
    try:
      ports = os.listdir(self._SERIAL_BASE)
    except IOError:
      logging.exception('Failed to lookup serial port.')
      sys.exit(1)
    if not ports:
      logging.error('Serial port is missing!')
      sys.exit(1)
    port = os.path.join(self._SERIAL_BASE, ports[0])
    logging.debug('Port: %s.', port)
    try:
      self._alarm = pima.Alarm(_parsed_args.zones, port)
    except pima.Error as e:
      logging.exception('Failed to create alarm class.')
      sys.exit(1)
    self._status = self._alarm.get_status()
    logging.info('Status: %s.', self._status)
    while not self._status['logged in']:
      self._status = self._alarm.login(_parsed_args.login)
      logging.info('Status: %s.', self._status)
    self._status_lock = threading.Lock()
    self._alarm_lock = threading.Lock()
    super(AlarmServer, self).__init__(name='PIMA Alarm Server')

  def __del__(self):
    if self._alarm:
      del self._alarm

  def run(self):
    """Continuously query the alarm for status."""
    while True:
      with self._alarm_lock:
        status = self._alarm.get_status()
        while not status['logged in']:
          # Re-login if previous session ended.
          status = self._alarm.login(_parsed_args.login)
        with self._status_lock:
          self._status = status
      logging.info('Status: %s.', self._status)
      time.sleep(1)

  def get_status(self) -> dict:
    """Gets the internally stored alarm status."""
    with self._status_lock:
      return self._status

  def arm(self, mode: pima.Arm, partitions: set) -> dict:
    """Arms (or disarms) the alarm, returning the status."""
    with self._alarm_lock:
      status = self._alarm.arm(mode, partitions)
      with self._status_lock:
        self._status = status
        logging.info('Status: %s.', self._status)
        return self._status

    
class HTTPRequestHandler(BaseHTTPRequestHandler):
  """Handler for PIMA alarm http requests."""
  _PIMA_URL = '/pima'
  _CMD_STATUS = 'status'
  _CMD_ARM = 'arm'

  class JsonEncoder(json.JSONEncoder):
    """Class for JSON encoding."""
    def default(self, obj):
      if isinstance(obj, set):
        return list(obj)
      return json.JSONEncoder.default(self, obj)

  def do_HEAD(self):
    """Return a JSON header."""
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()

  def do_GET(self):
    """Vaildate and run the request."""
    self.do_HEAD()
    logging.debug('Request: %s', self.path)
    parsed_url = urlparse(self.path)
    query = parse_qs(parsed_url.query)
    if not self.is_valid_url(parsed_url.path, query) or not _pima_server:
      self.write_json({'error': 'Invalid URL.'})
      return
    command = query['command'][0]
    if command == self._CMD_STATUS:
      self.write_json(_pima_server.get_status())
      return
    if command == self._CMD_ARM:
      try:
        mode = pima.Arm[query['mode'][0].upper()]
      except KeyError:
        self.write_json({'error': 'Invalid arm mode.'})
        return
      partitions = {int(p) for p in query.get('partitions', ['1'])}
      self.write_json(_pima_server.arm(mode, partitions))
      return
    self.write_json({'error': 'Invalid command.'})

  def write_json(self, data: dict):
    """Send out the provided data dict as JSON."""
    logging.debug('Response: %r', data)
    self.wfile.write(bytes(json.dumps(data, cls=self.JsonEncoder), 'utf-8'))

  @classmethod
  def is_valid_url(cls, path: str, query: dict):
    """Validate the provided URL."""
    if path != cls._PIMA_URL:
      return False
    if query.get('key',[''])[0] != _parsed_args.key:
      return False
    if query.get('command',[''])[0] not in {cls._CMD_STATUS, cls._CMD_ARM}:
      return False
    return True


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
                          help='Login code to the PIMA alarm')
  arg_parser.add_argument('-z', '--zones', type=int, default=32,
                          choices={32, 96, 144}, help='Alarm supported zones.')
  return arg_parser.parse_args()


if __name__ == '__main__':
  logging.basicConfig(format='{levelname[0]}{asctime}.{msecs:03.0f}  '
                      '{filename}:{lineno}] {message}', style='{',
                      datefmt='%m%d %H:%M:%S', level=logging.INFO)

  _parsed_args = ParseArguments()

  _pima_server = AlarmServer()
  _pima_server.start()

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
  del _pima_server
