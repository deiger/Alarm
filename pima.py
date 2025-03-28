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
import io
import logging
import serial
import socket
import termios
import time
import typing


class Error(Exception):
  """Error class for PIMA alarm handling."""
  pass


class GarbageInputError(Error):
  """Error class when PIMA alarm reports garbage."""
  pass


class Arm(enum.Enum):
  """Arming mode for the PIMA alarm."""
  FULL_ARM = b'\x01'
  HOME1 = b'\x02'
  HOME2 = b'\x03'
  DISARM = b'\x00'


Status = typing.NewType('Status', typing.Dict[str, typing.Any])
Partitions = typing.NewType('Partitions', typing.Set[int])
Zones = typing.NewType('Partitions', typing.Set[int])
Outputs = typing.NewType('Partitions', typing.Set[int])


class Alarm(object):
  """Class wrapping the protocol for PIMA alarm."""
  _ZONES_TO_MODULE_ID = {32: b'\x0d', 96: b'\x0d', 144: b'\x13'}
  _ZONES_TO_ZONE_BYTES = {32: 12, 96: 12, 144: 18}

  class _Message(enum.Enum):
    WRITE = b'\x0f'
    READ = b'\x0e'
    OPEN = b'\x01'
    CLOSE = b'\x19'
    STATUS = b'\x05'

  class _Channel(enum.Enum):
    IDLE = b'\x00'
    SYSTEM = b'\x01'
    ZONES = b'\x02'
    OUTPUTS = b'\x03'
    LOGIN = b'\x04'
    PARAMETER = b'\x05'

  _DISCRETE_FAILURES = {
      1: 'System Low Power',
      2: 'Unknown (2)',
      3: 'System Error',
      4: 'Zone Failure',
      5: 'Unknown (5)',
      6: 'Auxiliary Voltage Failure (Fuse short)',
      7: 'W/L Zone Low Battery',
      8: 'Wireless Receiver Failure',
      9: 'Low Battery',
      10: 'Telephone Line Failure',
      11: 'MAINS Failure (220V)',
      12: 'Tamper 1 Open',
      13: 'Tamper 2 Open',
      14: 'Clock Not Set',
      15: 'RAM Error',
      16: 'Station Commuincation Failure',
      17: 'Siren 1 Failure',
      18: 'Siren 2 Failure',
      19: 'SMS Communication',
      20: 'SMS Card',
      21: 'GSM200 Error',
      22: 'Network Comm. Fault',
      23: 'Radio Fault',
      24: 'Keyfob Rec. Fault',
      25: 'Wireless Receiver Tamper Open',
      26: 'Wireless Jamming',
      27: 'GSM-200 Failure',
      28: 'GSM Communication Failure',
      29: 'GSM-SIM Failure',
      30: 'GSM Link Failure',
      31: 'GSM Comm. Fault 2nd station',
      32: 'W/L Zone Supervision',
      33: 'Unknown (33)',
      34: 'Network fault Station 2',
      35: 'Net4Pro Fault',
      36: 'VVR 1 Fault',
      37: 'VVR 2 Fault',
      38: 'VVR 3 Fault',
      39: 'VVR 4 Fault',
      40: 'VVR 1 Power Fault',
      41: 'VVR 2 Power Fault',
      42: 'VVR 3 Power Fault',
      43: 'VVR 4 Power Fault',
      44: 'Unknown (44)',
      45: 'Unknown (45)',
      46: 'Unknown (46)',
      47: 'Unknown (47)',
      48: 'Unknown (48)',
  }

  def __init__(self,
               zones: int,
               serialport: str = None,
               ipaddr: str = None,
               ipport: int = None) -> None:
    if serialport is not None:
      try:
        self._channel = serial.Serial(port=serialport,
                                      baudrate=2400,
                                      bytesize=serial.EIGHTBITS,
                                      parity=serial.PARITY_NONE,
                                      timeout=1)
      except (termios.error, serial.serialutil.SerialException) as e:
        self._channel = None
        raise Error('Failed to connect to serial port.') from e
    else:
      try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ipaddr, ipport))
        self._channel = socket.SocketIO(sock, 'rwb')
      except (socket.error, socket.gaierror) as e:
        self._channel = None
        raise Error('Error creating socket.') from e
    self._crc = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0x0000, xorOut=0x0000)
    self._zones = zones  # type: int
    self._module_id = self._ZONES_TO_MODULE_ID[self._zones]  # type: bytes

  def __del__(self) -> None:
    self._close()

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback) -> None:
    self._close()

  def login(self, code: str) -> Status:
    data = bytes([int(digit) for digit in code]).ljust(6, b'\xff')
    self._read_message()
    self._send_message(self._Message.WRITE, self._Channel.LOGIN, data=data)
    return self.get_status()

  def get_status(self, max_retries=3) -> Status:
    """Returns the current alarm status.

    Args:
        max_retries: Maximum number of retry attempts for the entire status retrieval

    Returns:
        Status dictionary containing the alarm state
    """
    for attempt in range(max_retries):
      try:
        response = self._read_message()
        self._send_message(self._Message.STATUS, self._Channel.IDLE)
        data = Status({'logged in': False})

        if response and response[3:4] != self._Channel.SYSTEM.value:
          response = self._read_message()
          self._send_message(self._Message.STATUS, self._Channel.IDLE)

        if not response:
          return data

        if response[2:3] != self._Message.STATUS.value:
          if attempt < max_retries - 1:
            logging.debug('Invalid message type, retrying...')
            time.sleep(1)
            continue
          raise Error('Invalid message {}.'.format(self._make_hex(response[2:3])))

        if response[3:4] == self._Channel.IDLE.value:
          return data

        if response[3:4] != self._Channel.SYSTEM.value:
          if attempt < max_retries - 1:
            logging.debug('Invalid status channel, retrying...')
            time.sleep(1)
            continue
          raise Error('Invalid status {}.'.format(self._make_hex(response[3:4])))

        if response[4:7] != b'\x02\x00\x00':
          if attempt < max_retries - 1:
            logging.debug('Invalid address, retrying...')
            time.sleep(1)
            continue
          raise Error('Invalid address {}.'.format(self._make_hex(response[4:7])))

        # Rest of the processing remains the same
        zone_bytes = range(7, len(response), self._ZONES_TO_ZONE_BYTES[self._zones])[:5]
        zone_data = [response[i:i + self._zones // 8] for i in zone_bytes[:-1]]
        data['open zones'] = self._parse_bytes(zone_data[0])
        data['alarmed zones'] = self._parse_bytes(zone_data[1])
        data['bypassed zones'] = self._parse_bytes(zone_data[2])
        data['failed zones'] = self._parse_bytes(zone_data[3])

        index = zone_bytes[-1]
        data['partitions'] = {}
        for partition, value in enumerate(response[index:index + 16], 1):
          data['partitions'][partition] = Arm(bytes([value])).name.lower()

        index += 16
        failures = self._parse_bytes(response[index:index + 6])
        failures = {self._DISCRETE_FAILURES[failure] for failure in failures}

        index += 6
        for fail_type, count in (('Keypad %d Failure', 1), ('Keypad %d Tamper', 1),
                                 ('Zone Expander %d Failure', 2), ('Zone Expander %d Tamper', 2),
                                 ('Zone Expander %d Low Voltage',
                                  2), ('Zone Expander %d AC Failure',
                                       2), ('Zone Expander %d Low Battery',
                                            2), ('Out Expander %d Failure', 1),
                                 ('Out Expander %d Tamper', 1), ('Out Expander %d Low Voltage', 1),
                                 ('Out Expander %d AC Failure', 1), ('Out Expander %d Low Battery',
                                                                     1)):
          clustered_failures = self._parse_bytes(response[index:index + count])
          for failure in clustered_failures:
            failures.add(fail_type % failure)
          index += count

        if failures:
          data['failures'] = failures

        # Skip ID Account
        index += 4
        flags = response[index]
        data['logged in'] = bool(flags & 1 << 0)
        data['command ack'] = bool(flags & 1 << 1)
        return data

      except (GarbageInputError, Error) as e:
        if attempt < max_retries - 1:
          logging.debug('Status retrieval attempt %d failed: %s. Retrying...', attempt + 1, str(e))
          time.sleep(1)
          continue
        raise

    raise Error('Failed to get status after {} attempts'.format(max_retries))

  def arm(self, mode: Arm, partitions: Partitions) -> Status:
    """Arms (or disarms) the provided alarm partitions."""
    self._read_message()
    address = sum(1 << (p - 1) for p in partitions).to_bytes(2, byteorder='little')
    self._send_message(self._Message.OPEN if mode == Arm.DISARM else self._Message.CLOSE,
                       self._Channel.SYSTEM,
                       address=address,
                       data=mode.value)
    return self.get_status()

  def get_zones(self) -> Zones:
    """Gets the current status of the zones."""
    self._send_message(self._Message.READ, self._Channel.ZONES, address=b'\xff\xff', data=b'\x04')
    response = self._read_message()
    if response and response[3:4] == self._Channel.SYSTEM.value:
      self._send_message(self._Message.READ, self._Channel.ZONES, address=b'\xff\xff', data=b'\x04')
      response = self._read_message()
      self._send_message(self._Message.STATUS, self._Channel.IDLE)
    if not response:
      return Outputs()
    if response[3:4] != self._Channel.ZONES.value:
      raise Error('Invalid outputs response {}.'.format(self._make_hex(response)))
    if response[4:7] != b'\x02\xff\xff':
      raise Error('Invalid address {}.'.format(self._make_hex(response[4:7])))
    return Zones(self._parse_bytes(response[7:-1]))

  def get_outputs(self) -> Outputs:
    """Gets the currently alarming outputs."""
    self._send_message(self._Message.READ, self._Channel.OUTPUTS, address=b'\x00\x00')
    response = self._read_message()
    if response and response[3:4] == self._Channel.SYSTEM.value:
      self._send_message(self._Message.READ, self._Channel.OUTPUTS, address=b'\x00\x00')
      response = self._read_message()
      self._send_message(self._Message.STATUS, self._Channel.IDLE)
    if not response:
      return Outputs()
    if response[2:3] != b'\x05' and response[3:4] != self._Channel.OUTPUTS.value:
      raise Error('Invalid outputs response {}.'.format(self._make_hex(response)))
    if response[4:7] != b'\x02\x00\x00':
      raise Error('Invalid address {}.'.format(self._make_hex(response[4:7])))
    return Outputs(self._parse_bytes(response[7:], one_based=False))

  def get_parameters(self) -> Status:
    raise NotImplementedError("No support yet for parameters.")

  def _read_message(self, max_retries=3, retry_delay=0.5) -> bytes:
    """Read a message from the channel with retries.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay in seconds between retries

    Returns:
        The read message as bytes

    Raises:
        Error: If reading fails after all retries
        GarbageInputError: If only garbage data is received
    """
    last_error = None
    for attempt in range(max_retries):
      try:
        data = None
        while not data:
          data = self._channel.read(1)
          if not data and attempt < max_retries - 1:
            time.sleep(retry_delay)
            continue

        length = ord(data)
        data = bytes([length]) + self._channel.read(length + 2)

        # Check for garbage data
        if data == bytes([length]) * len(data):
          if attempt < max_retries - 1:
            time.sleep(retry_delay)
            continue
          raise GarbageInputError('Garbage ({})!'.format(length))

        # Check data length
        if len(data) != length + 3:
          if attempt < max_retries - 1:
            time.sleep(retry_delay)
            continue
          raise Error('Not enough data in channel: {} should have {} bytes.'.format(
              self._make_hex(data), length + 3))

        logging.debug('>>> ' + self._make_hex(data))
        data, crc = data[:-2], int.from_bytes(data[-2:], byteorder='big')

        # Validate CRC
        if (crc != self._crc(data)):
          if attempt < max_retries - 1:
            time.sleep(retry_delay)
            continue
          raise Error('Invalid input on channel, CRC for {} is {}, not {}!'.format(
              self._make_hex(data), self._crc(data), crc))

        # Validate module ID
        if self._module_id != data[1:2]:
          if attempt < max_retries - 1:
            time.sleep(retry_delay)
            continue
          raise Error('Invalid module ID. Expected {}, got {}'.format(
              self._make_hex(self._module_id), self._make_hex(data[1:2])))

        return data

      except (GarbageInputError, Error) as e:
        last_error = e
        if attempt < max_retries - 1:
          logging.debug('Attempt %d failed: %s. Retrying...', attempt + 1, str(e))
          time.sleep(retry_delay)
          continue

    # If we get here, all retries failed
    raise last_error or Error('Failed to read message after {} attempts'.format(max_retries))

  def _send_message(self,
                    message: _Message,
                    channel: _Channel,
                    address: bytes = b'',
                    data: bytes = b'') -> None:
    output = b''.join(
        (self._module_id, message.value, channel.value, bytes([len(address)]), address, data))
    output = bytes([len(output)]) + output
    output += self._crc(output).to_bytes(2, byteorder='big')
    logging.debug('<<< ' + self._make_hex(output))
    self._channel.write(output)
    if message != self._Message.STATUS:
      time.sleep(1)

  @staticmethod
  def _parse_bytes(data: bytes, one_based: bool = True) -> typing.Set[int]:
    bits = int.from_bytes(data, byteorder='little')
    base = 1 if one_based else 0
    return {i + base for i in range(bits.bit_length()) if bits & 1 << i}

  @staticmethod
  def _make_hex(data: bytes) -> str:
    return ' '.join('%02x' % d for d in data)

  def _close(self) -> None:
    if self._channel:
      self._channel.close()
      self._channel = None
