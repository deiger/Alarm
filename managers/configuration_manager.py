import logging
import argparse
import os
from typing import Optional, List

from helpers.const import *

_LOGGER = logging.getLogger(__name__)


class ConfigurationManager:
    api_web_ssl_cert: Optional[str]
    api_web_ssl_key: Optional[str]
    api_web_port: Optional[int]
    api_key: Optional[str]
    pima_login: Optional[str]
    pima_zones: Optional[int]
    pima_serial_port: Optional[str]
    pima_host: Optional[str]
    pima_port: Optional[int]
    mqtt_host: Optional[str]
    mqtt_port: Optional[int]
    mqtt_client_id: Optional[str]
    mqtt_user: Optional[str]
    mqtt_password: Optional[str]
    mqtt_topic: Optional[str]
    log_level: Optional[str]
    is_ssl: Optional[bool]
    can_connect: Optional[bool]

    def __init__(self):
        api_mode = os.getenv("API_MODE", "CMD")

        self.api_binds = SERVER_BIND

        if api_mode == "CMD":
            args = self.get_args()

            self.api_ssl_cert = args.ssl_cert
            self.api_ssl_key = args.ssl_key
            self.api_port = args.port
            self.api_key = args.key
            self.login = args.login
            self.pima_zones = args.zones
            self.pima_serial_port = args.serialport
            self.pima_host = args.pima_host
            self.pima_port = args.pima_port
            self.mqtt_host = args.mqtt_host
            self.mqtt_port = args.mqtt_port
            self.mqtt_client_id = args.mqtt_client_id
            self.mqtt_topic = args.mqtt_topic
            self.log_level = args.log_level

            mqtt_user_parts = args.mqtt_user.split(':', 1)
            if len(mqtt_user_parts) > 1:
                self.mqtt_username = mqtt_user_parts[0]
                self.mqtt_password = mqtt_user_parts[0]

        else:
            self.api_ssl_cert = os.getenv("API_SSL_CERT")
            self.api_ssl_key = os.getenv("API_SSL_KEY")
            self.api_port = os.getenv("API_PORT")
            self.api_key = os.getenv("API_KEY")
            self.pima_login = os.getenv("PIMA_LOGIN")
            self.pima_zones = os.getenv("PIMA_ZONES")
            self.pima_serial_port = os.getenv("PIMA_SERIAL_PORT")
            self.pima_host = os.getenv("PIMA_HOST")
            self.pima_port = os.getenv("PIMA_PORT")
            self.mqtt_host = os.getenv("MQTT_HOST")
            self.mqtt_port = os.getenv("MQTT_PORT")
            self.mqtt_client_id = os.getenv("MQTT_CLIENT_ID")
            self.mqtt_username = os.getenv("MQTT_USERNAME")
            self.mqtt_password = os.getenv("MQTT_PASSWORD")
            self.mqtt_topic = os.getenv("MQTT_TOPIC", "pima_alarm")
            self.log_level = os.getenv("LOG_LEVEL", LOG_LEVEL_INFO)

        self.is_ssl = self._has_valid_content(self.api_ssl_key) and self._has_valid_content(self.api_ssl_cert)
        self.ssl_context = None
        self.is_debug = self.log_level == "DEBUG"

        if self.is_ssl:
            self.ssl_context = (self.api_ssl_cert, self.api_ssl_key)

        self.can_connect = False

        if self.pima_host and self.pima_port:
            # Connected by ethernet
            _LOGGER.debug(f"IP Address: {self.pima_host}:{self.pima_port}.")

            self.can_connect = True

        elif self.pima_serial_port:
            # Connected by Serial
            _LOGGER.debug(f"Port: {self.pima_serial_port}.")

            self.can_connect = True

        else:
            # Connected by serial port
            try:
                ports = os.listdir(SERIAL_BASE)  # type: List[str]

                if ports:
                    self.can_connect = True

                    self.pima_serial_port = os.path.join(SERIAL_BASE, ports[0])

                    _LOGGER.debug(f"Port: {self.pima_serial_port}.")

                else:
                    _LOGGER.error('Serial port is missing!')

            except IOError:
                _LOGGER.exception('Failed to lookup serial port.')

    @staticmethod
    def get_args() -> argparse.Namespace:
        """Parse command line arguments."""
        arg_parser = argparse.ArgumentParser(
            description='JSON server for PIMA alarms.',
            allow_abbrev=False)

        for item in ARGS:
            short_key = item.get(ARG_SHORT_KEY)

            if short_key is None:
                arg_parser.add_argument(f"--{item.get(ARG_KEY)}",
                                        help=item.get(ARG_HELP),
                                        default=item.get(ARG_DEFAULT),
                                        required=item.get(ARG_REQUIRED, False),
                                        type=item.get(ARG_TYPE),
                                        choices=item.get(ARG_CHOICES)
                                        )

            else:
                arg_parser.add_argument(f"-{short_key}",
                                        f"--{item.get(ARG_KEY)}",
                                        help=item.get(ARG_HELP),
                                        default=item.get(ARG_DEFAULT),
                                        required=item.get(ARG_REQUIRED, False),
                                        type=item.get(ARG_TYPE),
                                        choices=item.get(ARG_CHOICES)
                                        )

        parsed_args = arg_parser.parse_args()

        return parsed_args

    @staticmethod
    def _has_valid_content(data):
        return data is not None and data != ""
