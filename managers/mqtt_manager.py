from typing import Optional
from paho.mqtt.client import Client, MQTTMessage
from os import path

from helpers.const import CMD_STATUS, CMD_ARM
from helpers.json_helper import to_json
from managers.configuration_manager import ConfigurationManager

import socket
import logging
from time import sleep

_LOGGER = logging.getLogger(__name__)


class MQTTManager:
    def __init__(self, configuration_manager: ConfigurationManager, callback):
        self._mqtt_client = None  # type: Optional[Client]
        self._configuration_manager = configuration_manager
        self._topic_subscribe = None
        self._topic_publish = None
        self._topic_lwt = None
        self._callback = callback

        self._is_ready = False

        this = self

        def mqtt_on_connect(client: Client, userdata, flags, rc):
            _LOGGER.error("MQTT Client connected")

            client.subscribe(this._topic_subscribe)

        def mqtt_on_disconnect(client: Client, userdata, flags, rc):
            _LOGGER.error("MQTT Client disconnected")

            this._is_ready = False

            this.connect()

        def mqtt_on_message(client: Client, userdata, message: MQTTMessage):
            result = self._callback(message.payload)

            this.publish_status(result)

        self._mqtt_on_connect = mqtt_on_connect
        self._mqtt_on_disconnect = mqtt_on_disconnect
        self._mqtt_on_message = mqtt_on_message

    def _get_topic(self, key):
        topic = path.join(self._configuration_manager.mqtt_topic, key)

        return topic

    def connect(self):
        if self._configuration_manager.mqtt_host:
            self._topic_publish = self._get_topic(CMD_STATUS)
            self._topic_subscribe = self._get_topic(CMD_ARM)
            self._topic_lwt = self._get_topic('LWT')

            self._mqtt_client = Client(client_id=self._configuration_manager.mqtt_client_id,
                                       clean_session=True)

            self._mqtt_client.on_connect = self._mqtt_on_connect
            self._mqtt_client.on_disconnect = self._mqtt_on_disconnect
            self._mqtt_client.on_message = self._mqtt_on_message

            if self._configuration_manager.mqtt_username and self._configuration_manager.mqtt_password:
                self._mqtt_client.username_pw_set(self._configuration_manager.mqtt_username,
                                                  self._configuration_manager.mqtt_password)

            self._mqtt_client.will_set(self._topic_lwt, payload='offline', retain=True)

            while True:
                try:
                    self._mqtt_client.connect(self._configuration_manager.mqtt_host,
                                              self._configuration_manager.mqtt_port)

                    self._is_ready = True
                except (socket.timeout, OSError):
                    _LOGGER.exception('Failed to connect to MQTT broker. Retrying in 5 seconds...')
                    sleep(5)
                else:
                    break

            self._mqtt_publish_lwt_online()
            self._mqtt_client.loop_start()

    def publish_status(self, status: dict) -> None:
        if self._is_ready:
            self._mqtt_client.publish(self._topic_publish, payload=to_json(status))

    def _mqtt_publish_lwt_online(self) -> None:
        if self._is_ready:
            self._mqtt_client.publish(self._topic_lwt, payload='online', retain=True)
