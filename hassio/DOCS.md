# Home Assistant Add-on: PIMA Alarms

## Prerequisites

1. PIMA Hunter Pro alarm&trade;, with 32, 96 or 144 zones.
1. PIMA Home Automation kit&trade; (`SA-232`, `LCL-11A` and Serial-to-USB cable), or `net4pro` ethernet connection.
   Diagram by PIMA&trade; &copy;:
   ![Diagram by PIMA&trade; &copy;](home_automation_kit.png)
   - According to various users, the alarm can be alternatively connected using a `PL2303TA` USB-to-TTL cable, like [this one](https://www.aliexpress.com/item/32345829369.html).
   - Yet another option is to connect directly to Raspberry pi, as specified here:
   ![Diagram by @maorcc](rpi_connection.png)
1. Raspberry Pi or similar, connected to the alarm through the Home Automation kit.
   - Tested on [Raspbian](https://www.raspberrypi.org/downloads/raspbian/). Other operating systems
     may use different path structure for the serial ports.
1. Alarm technician login code. Unfortunately, it is not possible to connect to the alarm using a user login code.
1. An [MQTT broker](https://www.home-assistant.io/docs/mqtt/broker/) installed,
   whether it is Mosquitto or the default Home Assistant MQTT broker. Please
   make sure to install and set up that add-on before continuing.

# Configuration

1. Enable the alarm control by following the instructions
   [here](https://github.com/deiger/Alarm#enabling-the-alarm-serial-port-or-network-connection).
1. Set the configuration as follows:
   ```yaml
   log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL. Default is INFO.
   login: The technician login code to the alarm.
   zones: Number of zones supported by the alarm, one of 32, 96 or 144. Default is 32.
   serialport: Serial port, e.g. `/dev/serial0`. Needed if connected directly through GPIO serial.
   pima_host: Pima alarm hostname or IP address. Must be set if connected by ethernet.
   pima_port: Pima alarm port. Must be set if connected by ethernet.
   mqtt_host: The MQTT broker hostname or IP address.
   mqtt_port: The MQTT broker port. Default is 1883.
   mqtt_client_id: The MQTT client ID. If not set, a random client ID will be generated.
   mqtt_user: User name for MQTT server. Remove if no authentication is used.
   mqtt_pass: Password for MQTT server. Remove if no authentication is used.
   mqtt_topic: The MQTT root topic. Default is &quot;pima_alarm&quot;. The server will listen on topic &lt;{mqtt_topic}/command&gt; and publish to &lt;{mqtt_topic}/status&gt;.
   mqtt_discovery_max_zone: The highest number to enable for MQTT discovery (to avoid adding sensors for inoperative zones).
   key: An arbitrary string key to authenticate the server calls. Consider generating a random key using `uuid -v4`.
   port: Port number for the web server.
   ```
