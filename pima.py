#!/usr/bin/env python3
"""
This module implements an interface for negotiation with PIMA Hunter Pro alarms.
It was built based on PIMA's General Specification for Home Automation &
Building Management protocol Ver. 1.15.
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

import collections
import crcmod
import enum
import logging
import serial
import termios
import time


class Error(Exception):
  """Error class for PIMA alarm handling."""
  pass


class Arm(enum.Enum):
  """Arming mode for the PIMA alarm."""
  FULL_ARM = b'\x01'
  HOME1    = b'\x02'
  HOME2    = b'\x03'
  DISARM   = b'\x00'


class Alarm(object):
  """Class wrapping the protocol for PIMA alarm."""
  _ZONES_TO_MODULE_ID = {32: b'\x0d', 96: b'\x0d', 144: b'\x13'}
  _ZONES_TO_ZONE_BYTES = {32: 12, 96: 12, 144: 18}
  class _Message(enum.Enum):
    WRITE  = b'\x0f'
    READ   = b'\x0e'
    OPEN   = b'\x01'
    CLOSE  = b'\x19'
    STATUS = b'\x05'
  class _Channel(enum.Enum):
    IDLE      = b'\x00'
    SYSTEM    = b'\x01'
    ZONES     = b'\x02'
    OUTPUTS   = b'\x03'
    LOGIN     = b'\x04'
    PARAMETER = b'\x05'

  def __init__(self, zones: int, port: int):
    try:
      self._channel = serial.Serial(port=port,
                                    baudrate=2400,
                                    bytesize=serial.EIGHTBITS,
                                    parity=serial.PARITY_NONE,
                                    timeout=1)
    except (termios.error, serial.serialutil.SerialException) as e:
      self._channel = None
      raise Error('Failed to connect to serial port.') from e
    self._crc = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0x0000, xorOut=0x0000)
    self._zones = zones
    self._module_id = self._ZONES_TO_MODULE_ID[self._zones]
  
  def __del__(self):
    self._close()

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self._close()

  def login(self, code: str) -> bytes:
    data = bytes([int(digit) for digit in code]).ljust(6, b'\xff')
    self._read_message()
    self._send_message(self._Message.WRITE, self._Channel.LOGIN, data=data)
    return self.get_status()

  def get_status(self) -> dict:
    """Returns the current alarm status."""
    try:
      response = self._read_message()
    except Error as ex:
      logging.info('Exception: %r.', ex)
      # Clear up a messy channel (sometime happens on startup).
      d = b'\xf3'
      while d == d[:1] * len(d):
        d = self._channel.readline()
        logging.debug('Read message: %r.', d)
      response = self._read_message()
    self._send_message(self._Message.STATUS, self._Channel.IDLE)
    data = {'logged in': False}
    if not response:
        return data
    if response[2:3] != self._Message.STATUS.value:
      raise Error('Invalid message {}.'.format(self._make_hex(response[2:3])))
    if response[3:4] == self._Channel.IDLE.value:
      return data
    if response[3:4] != self._Channel.SYSTEM.value:
      raise Error('Invalid status {}.'.format(self._make_hex(response[3:4])))
    if response[4:7] != b'\x02\x00\x00':
      raise Error('Invalid address {}.'.format(self._make_hex(response[4:7])))
    # Calculate the break points.
    zone_bytes = range(7, len(response),
                       self._ZONES_TO_ZONE_BYTES[self._zones])[:5]
    # Get the data chuncks.
    # HP32 zones us using only the first bytes.
    zone_data = [response[i:i + self._zones // 8] for i in zone_bytes[:-1]]
    data['open zones'] = self._parse_zones(zone_data[0])
    data['alarmed zones'] = self._parse_zones(zone_data[1])
    data['bypassed zones'] = self._parse_zones(zone_data[2])
    data['failed zones'] = self._parse_zones(zone_data[3])
    index = zone_bytes[-1]
    data['partitions'] = collections.defaultdict(set)
    for partition, value in enumerate(response[index:index+16], 1):
      data['partitions'][Arm(bytes([value])).name.lower()].add(partition)
    index += 16
    for fail_type, count in (('discrete failures', 6),
                             ('keypads failures', 2),
                             ('zone expander failures', 10),
                             ('relay expander failures', 5)):
      failures = response[index:index+count]
      if failures != b'\x00' * count:
        data[fail_type] = failures
      index += count
    # Skip ID Account
    index += 4
    flags = response[index]
    data['logged in'] = bool(flags & 1 << 0)
    data['command ack'] = bool(flags & 1 << 1)
    return data

  def arm(self, mode: Arm, partitions: set) -> bytes:
    """Arms (or disarms) the provided alarm partitions."""
    self._read_message()
    address = sum(1<<(p-1) for p in partitions).to_bytes(2, byteorder='little')
    self._send_message(
        self._Message.OPEN if mode == Arm.DISARM else self._Message.CLOSE,
        self._Channel.SYSTEM, address=address, data=mode.value)
    return self.get_status()

  def zones(self) -> bytes:
    raise NotImplementedError("No support yet for zones.")

  def outputs(self) -> bytes:
    raise NotImplementedError("No support yet for outputs.")

  def parameters(self) -> bytes:
    raise NotImplementedError("No support yet for parameters.")

  def _read_message(self) -> bytes:
    data = None
    while not data:
      data = self._channel.read(1)
    length = ord(data)
    data = bytes([length]) + self._channel.read(length + 2)
    if data == bytes([length]) * len(data):
      raise Error('Garbage ({})!'.format(length))
    logging.debug('>>> ' + self._make_hex(data))
    data, crc = data[:-2], int.from_bytes(data[-2:], byteorder='big')
    if (crc != self._crc(data)):
      raise Error('Invalid input on channel, CRC for {} is {}, not {}!'.format(
          self._make_hex(data), self._crc(data), crc))
    if self._module_id != data[1:2]:
      raise Error('Invalid module ID. Expected {}, got {}'.format(
          self._make_hex(self._module_id), self._make_hex(data[1:2])))
    return data

  def _send_message(self, message: _Message, channel: _Channel,
                    address: bytes=b'', data: bytes=b'') -> bytes:
    output = b''.join((self._module_id, message.value, channel.value,
                       bytes([len(address)]), address, data))
    output = bytes([len(output)]) + output
    output += self._crc(output).to_bytes(2, byteorder='big')
    logging.debug('<<< ' + self._make_hex(output))
    self._channel.write(output)
    if message != self._Message.STATUS:
      time.sleep(1)

  @staticmethod
  def _parse_zones(data: bytes) -> set:
    bits = int.from_bytes(data, byteorder='little')
    return {i+1 for i in range(bits.bit_length()) if bits & 1 << i}
    
  @staticmethod
  def _make_hex(data: bytes) -> str:
    return ' '.join('%02x' % d for d in data)
    
  def _close(self):
    if self._channel:
      self._channel.close()
      self._channel = None
  