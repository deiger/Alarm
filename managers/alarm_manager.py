from http.server import HTTPServer
import json
import logging
import threading
from time import sleep
from typing import Optional

import _thread
from api import pima
from helpers.const import CMD_ARM, CMD_STATUS
from managers.configuration_manager import ConfigurationManager
from managers.mqtt_manager import MQTTManager

_LOGGER = logging.getLogger(__name__)


class AlarmManager(threading.Thread):
    """Class maintaining the current status and sends commands to the alarm."""

    def __init__(self, configuration_manager: ConfigurationManager) -> None:
        self._mqtt_manager: MQTTManager = MQTTManager(
            configuration_manager, self._callback
        )
        self._alarm: Optional[pima.Alarm] = None
        self._httpd: Optional[HTTPServer] = None
        self._configuration_manager = configuration_manager
        self._alarm_args = None
        self._status_lock = None
        self._alarm_lock = None
        self._status = None
        self._is_ready = False

        super().__init__(name="PIMA Alarm Server")

    def initialize(self):
        try:
            if self._configuration_manager.can_connect:
                self._create_alarm()

                self._status_lock = threading.Lock()
                self._alarm_lock = threading.Lock()

                self._is_ready = True
        except pima.Error:
            _LOGGER.exception("Failed to create alarm object.")

    def __del__(self) -> None:
        if self._alarm:
            del self._alarm

    def run(self) -> None:
        """Continuously query the alarm for status."""
        while True:
            try:
                with self._alarm_lock:
                    status = self._alarm.get_status()  # type: pima.Status
                    while not status["logged in"]:
                        # Re-login if previous session ended.
                        status = self._alarm.login(
                            self._configuration_manager.pima_login
                        )

                    self._set_status(status)
                sleep(1)

            except Exception as ex:
                logging.exception(f"Exception raised by Alarm, Error: {ex}")
                try:
                    with self._alarm_lock:
                        _LOGGER.info("Trying to create the Alarm anew.")
                        self._create_alarm()

                except pima.Error:
                    _LOGGER.exception(
                        "Failed to recreate Alarm object. Exit for a clean restart."
                    )
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

        _LOGGER.info(f"Status: self._status.")

        self._mqtt_manager.publish_status(status)

    def _create_alarm(self) -> None:
        configuration_manager = self._configuration_manager

        self._alarm = pima.Alarm(
            configuration_manager.pima_zones,
            configuration_manager.pima_serial_port,
            configuration_manager.pima_host,
            configuration_manager.pima_port,
        )  # type: pima.Alarm

        self._status = self._alarm.get_status()  # type: pima.Status

        _LOGGER.info(f"Status: {self._status}.")

        while not self._status["logged in"]:
            self._status = self._alarm.login(self._configuration_manager.pima_login)

            _LOGGER.info(f"Status: {self._status}.")

    def _callback(self, payload: bytes):
        payload_str = payload.decode("utf-8")
        data = json.loads(payload_str)

        result = self.execute(CMD_ARM, data)

        error = result.get("error")

        if error is not None:
            _LOGGER.error(f"Failed to run arm, Error: {error}, data: {data}")

        self._mqtt_manager.publish_status(result)

    def execute(self, command: str, data: Optional[dict] = None):
        message = {}

        try:
            handled = False

            if command is None:
                message["error"] = "Missing command"

                handled = True
            else:
                if isinstance(command, list):
                    command = command[0]

            if not self._is_ready:
                message["error"] = "No Server"
                handled = True

            if not handled and command == CMD_STATUS:
                message = self.get_status()
                handled = True

            if not handled and command == CMD_ARM:
                mode = data.get("mode")

                try:
                    if isinstance(mode, list):
                        mode = mode[0]

                    mode = pima.Arm[mode.upper()]

                    partitions = pima.Partitions(
                        {int(p) for p in data.get("partitions", ["1"])}
                    )

                    message = self.arm(mode, partitions)

                except KeyError:
                    message["error"] = f"Invalid arm mode [{mode}]"

                handled = True

            if not handled:
                message["error"] = f"Invalid command"

        except Exception as ex:
            _LOGGER.error(f"Failed to run command due to error: {ex}, data: {data}")

        return message
