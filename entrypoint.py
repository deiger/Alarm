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

import logging
from managers.alarm_manager import AlarmManager
from flask import Flask, request, abort, jsonify
from threading import Thread

from managers.configuration_manager import ConfigurationManager
from helpers.const import PIMA_URL, CMD_STATUS, PIMA_STATUS_URL, PIMA_ARM_URL, CMD_ARM, ARM_MODE, SUPPORTED_ARM_MODES

_LOGGER = logging.getLogger(__name__)

app = Flask(__name__)
configuration_manager = ConfigurationManager()

manager = AlarmManager(configuration_manager)
initialize_thread = Thread(target=manager.initialize)
initialize_thread.start()


def validate_key(key):
    key = request.args.get('api_key')
    is_valid = key == configuration_manager.api_key

    if not is_valid:
        _LOGGER.warning(f"Unauthorized request using key '{key}'")

    return is_valid


@app.route(PIMA_STATUS_URL, methods=['GET'])
def pima_get_status_handler():
    key = request.args.get('api_key')
    is_valid_request = validate_key(key)

    if is_valid_request:
        result = manager.execute(CMD_STATUS)

        content = jsonify(result)

        return content

    else:
        _LOGGER.error(f"Unauthorized request")

        abort(401, description="Unauthorized request")


@app.route(PIMA_ARM_URL, methods=['POST'])
def pima_post_arm_handler():
    key = request.args.get('api_key')
    is_valid_request = validate_key(key)

    if is_valid_request:
        if request.data:
            data = request.get_json(force=True)

            arm_mode = data.get(ARM_MODE)

            if arm_mode is None or arm_mode not in SUPPORTED_ARM_MODES:
                _LOGGER.error(f"Invalid arm mode, must be one of {SUPPORTED_ARM_MODES}")

                abort(501, f"Invalid arm mode, must be one of {SUPPORTED_ARM_MODES}")

            else:
                result = manager.execute(CMD_ARM, data)

                content = jsonify(result)

                return content

        else:
            _LOGGER.error(f"Invalid request data")

            abort(400, "Invalid request data")

    else:
        _LOGGER.error(f"Unauthorized request")

        abort(401, description="Unauthorized request")


app.run(host=configuration_manager.api_binds,
        port=configuration_manager.api_port,
        debug=configuration_manager.is_debug,
        ssl_context=configuration_manager.ssl_context)
