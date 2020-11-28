from helpers.login_codes import LoginCodes

CMD_STATUS = "status"
CMD_ARM = "arm"
SERIAL_BASE = "/dev/serial/by-path"
SERVER_BIND = "0.0.0.0"
PIMA_URL = "/pima"
PIMA_STATUS_URL = f"{PIMA_URL}/{CMD_STATUS}"
PIMA_ARM_URL = f"{PIMA_URL}/{CMD_ARM}"

ARM_MODE = "mode"
ARM_FULL = "full_arm"
ARM_HOME1 = "home1"
ARM_HOME2 = "home2"
ARM_DISARM = "disarm"
SUPPORTED_ARM_MODES = [ARM_FULL, ARM_HOME1, ARM_HOME2, ARM_DISARM]

LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

ARG_LOG_LEVEL_KEY = "--log_level"
ARG_LOG_LEVEL_DEFAULT = LOG_LEVEL_INFO
ARG_LOG_LEVEL_CHOICES = {
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_CRITICAL,
}
ARG_LOG_LEVEL_HELP = "Minimal log level"

ARG_SHORT_KEY = "short-key"
ARG_KEY = "key"
ARG_HELP = "help"
ARG_TYPE = "type"
ARG_REQUIRED = "required"
ARG_DEFAULT = "default"
ARG_CHOICES = "choices"

ARGS = [
    {ARG_KEY: "ssl_cert", ARG_HELP: "Path to SSL certificate file"},
    {ARG_KEY: "ssl_key", ARG_HELP: "Path to SSL key file"},
    {
        ARG_SHORT_KEY: "p",
        ARG_KEY: "port",
        ARG_HELP: "Port for the server",
        ARG_REQUIRED: True,
        ARG_TYPE: int,
    },
    {
        ARG_SHORT_KEY: "k",
        ARG_KEY: "key",
        ARG_HELP: "URL key to authenticate calls",
        ARG_REQUIRED: True,
    },
    {
        ARG_SHORT_KEY: "l",
        ARG_KEY: "login",
        ARG_HELP: "Login code to the PIMA alarm",
        ARG_CHOICES: LoginCodes(),
        ARG_REQUIRED: True,
    },
    {
        ARG_SHORT_KEY: "z",
        ARG_KEY: "zones",
        ARG_HELP: "Alarm supported zones",
        ARG_TYPE: int,
        ARG_DEFAULT: 32,
        ARG_CHOICES: {32, 96, 144},
    },
    {
        ARG_KEY: "serialport",
        ARG_HELP: "Serial port, e.g. /dev/serial0. Needed if connected directly through GPIO serial",
    },
    {
        ARG_KEY: "pima_host",
        ARG_HELP: "Pima alarm hostname or IP address. if connected by ethernet",
    },
    {
        ARG_KEY: "pima_port",
        ARG_HELP: "Pima alarm port. if connected by ethernet",
        ARG_TYPE: int,
    },
    {ARG_KEY: "mqtt_host", ARG_HELP: "MQTT broker hostname or IP address"},
    {ARG_KEY: "mqtt_port", ARG_HELP: "MQTT broker port", ARG_TYPE: int},
    {ARG_KEY: "mqtt_client_id", ARG_HELP: "MQTT client id"},
    {ARG_KEY: "mqtt_user", ARG_HELP: "<user:password> for the MQTT channel"},
    {ARG_KEY: "mqtt_topic", ARG_HELP: "MQTT topic", ARG_DEFAULT: "pima_alarm"},
    {
        ARG_KEY: ARG_LOG_LEVEL_KEY,
        ARG_HELP: ARG_LOG_LEVEL_HELP,
        ARG_CHOICES: ARG_LOG_LEVEL_CHOICES,
        ARG_DEFAULT: ARG_LOG_LEVEL_DEFAULT,
    },
]
