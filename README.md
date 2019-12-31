# PIMA Alarms

This program implements an interface for negotiation with [PIMA Hunter Pro alarms](https://www.pima-alarms.com/our-products/hunter-pro-series/).  
It was built based on PIMA&trade;'s General Specification for Home Automation &
Building Management protocol Ver. 1.15.  
PIMA&trade; is a trademark of PIMA Electronic Systems Ltd, http://www.pima-alarms.com.  
This program was built with no affiliation of PIMA Electronic Systems Ltd.

## Prerequisites
1. PIMA Hunter Pro alarm&trade;, with 32, 96 or 144 zones.
1. PIMA Home Automation kit&trade; (`SA-232`, `LCL-11A` and Serial-to-USB cable), or `net4pro` ethernet connection.
   Diagram by PIMA&trade; &copy;:
   ![Diagram by PIMA&trade; &copy;](home_automation_kit.png)
1. Raspberry Pi or similar, connected to the alarm through the Home Automation kit.
   - Tested on [Raspbian](https://www.raspberrypi.org/downloads/raspbian/). Other operating systems
     may use different path structure for the serial ports.
1. Alarm technician login code. Unfortunately, it is not possible to connect to the alarm using a user login code.

## Enabling the alarm serial port or network connection
1. Enable extended menus:
   - Primary login code
   - `NEXT`
   - Technician login code
   - `5` (General parameters)
   - `ENTR`
   - `NEXT` till you get to the right `P` (extended menus)
   - Toggle by `#`
   - `ENTR`
   - `END` to exit
1. Enable the serial port:
   - Primary login code
   - `NEXT`
   - Technician login code
   - `3` (Communication)
   - `ENTR`
   - 8 x `NEXT` (Serial port)
   - `ENTR`
   - Toggle the first `L` (for serial connection) or first `N` (for net4pro) by `#`
   - `ENTR`
   - `END` to exit

## Setup
1. Create an SSL certificate, if you wish to access the server through HTTPS:
   ```bash
   openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
   ```
1. Install additional Python libraries:
   ```bash
   pip3 install crcmod paho-mqtt pyserial
   ```
1. Download [pima.py](pima.py) and [pima_server.py](pima_server.py), and put them in the same directory.
1. Set run permissions to [pima_server.py](pima_server.py):
   ```bash
   chmod a+x pima_server.py
   ```
## Run for testing
1. Test out that you can run the server, e.g.:
   ```bash
   ./pima_server.py --ssl_cert cert.pem --ssl_key key.pem --port 7777 --key my_random_key --login 000000 --mqtt_host localhost
   ```
   Parameters:
   - `--ssl_cert` - Path to the SSL certificate file. If not set, will run a non-encrypted web server.
   - `--ssl_key` - Path to the SSL private key file. If not set, will get the key from the certificate file.
   - `--port` or `-p` - Port for the web server.
   - `--key` or `-k` - An arbitrary string key to authenticate the server calls.  
     Consider generating a random key using `uuid -v4`.
   - `--login` or `-l` - The technician login code to the alarm.
   - `--zones` or `-z` - Number of zones supported by the alarm, one of 32, 96 or 144. Default is 32.
   - `--serialport` - Serial port, e.g. `/dev/serial0`. Needed if connected directly through GPIO serial.
   - `--pima_host` - Pima alarm hostname or IP address. Must be set if connected by ethernet.
   - `--pima_port` - Pima alarm port. Must be set if connected by ethernet.
   - `--mqtt_host` - The MQTT broker hostname or IP address. Must be set to enable MQTT.
   - `--mqtt_port` - The MQTT broker port. Default is 1883.
   - `--mqtt_client_id` - The MQTT client ID. If not set, a random client ID will be generated.
   - `--mqtt_user` - &lt;user:password&gt; for the MQTT channel. If not set, no authentication is used.
   - `--mqtt_topic` - The MQTT root topic. Default is &quot;pima_alarm&quot;. The server will listen on topic
     &lt;{mqtt_topic}/command&gt; and publish to &lt;{mqtt_topic}/status&gt;.
   - `--log_level` - The minimal log level to send to syslog. Default is WARNING.
1. Access e.g. using curl:
   ```bash
   curl -ik 'http://localhost:7777/pima?key=my_random_key&command=status'
   curl -ik 'http://localhost:7777/pima?key=my_random_key&command=arm&mode=home1&partitions=1'
   ```
   CGI Arguments:
   - `key` - The key specified on the web server startup.
   - `command` - Either `status` or `arm`.  
      When `arm` is specified:
      - `mode` - Either `full_arm`, `home1`, `home2` or `disarm`.
      - `partitions` Comma separated list of partitions. Default is `1`.
## Run as a service
1. Create a dedicated directory for the script files, and move the files to it.
   Pass the ownership to root. e.g.:
   ```bash
   sudo mkdir /usr/lib/pima
   sudo mv pima_server.py pima.py key.pem cert.pem /usr/lib/pima
   sudo chown root:root /usr/lib/pima/*
   sudo pip3 install crcmod paho-mqtt pyserial
   ```
1. Create a service configuration file (as root), e.g. `/lib/systemd/system/pima.service`:
   ```INI
   [Unit]
   Description=PIMA alarm server
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 -u pima_server.py --ssl_cert cert.pem --ssl_key key.pem --port 7777 --key my_random_key --login 000000 --mqtt_host localhost
   WorkingDirectory=/usr/lib/pima
   StandardOutput=inherit
   StandardError=inherit
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
1. Link to it from `/etc/systemd/system/`:
   ```bash
   sudo ln -s /lib/systemd/system/pima.service /etc/systemd/system/multi-user.target.wants/pima.service
   ```
1. Enable and start the new service:
   ```bash
   sudo systemctl enable pima.service
   sudo systemctl start pima.service
   ```
1. If you use [MQTT](http://en.wikipedia.org/wiki/Mqtt) for [HomeAssistant](https://www.home-assistant.io/) or
   [openHAB](https://www.openhab.org/), the broker should now provide the updated status of the alarm, and accepts commands.
## Next steps
1. [Groovy](http://groovy-lang.org/) [Device Type Handlers](https://docs.smartthings.com/en/latest/device-type-developers-guide/) for [SmartThings](https://www.smartthings.com/) integration.
1. Support further functionality, e.g. change user codes.
