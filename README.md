# PIMA Alarms

This program implements an interface for negotiation with [PIMA Hunter Pro alarms](https://www.pima-alarms.com/our-products/hunter-pro-series/).  
It was built based on PIMA&trade;'s General Specification for Home Automation &
Building Management protocol Ver. 1.15.  
PIMA&trade; is a trademark of PIMA Electronic Systems Ltd, http://www.pima-alarms.com.  
This program was built with no affiliation of PIMA Electronic Systems Ltd.

## Prerequisites
1. PIMA Hunter Pro alarm&trade;, with 32, 96 or 144 zones.
1. PIMA Home Automation kit&trade; (SA-232, LCL-11A and Serial-to-USB cable).  
   Diagram by PIMA&trade; &copy;:
   ![Diagram by PIMA&trade; &copy;](home_automation_kit.png)
1. Raspberry Pi or similar, connected to the alarm through the Home Automation kit.
   - Tested on [Raspbian](https://www.raspberrypi.org/downloads/raspbian/). Other operating systems
     may use different path structure for the serial ports.
1. Alarm installer login code. Unfortunately, it is not possible to connect to the alarm using a user login code.

## Setup
1. Create an SSL certificate, if you wish to access the server through HTTPS:
   ```bash
   openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
   ```
1. Install additional Python libraries:
   ```bash
   pip3 install crcmod pyserial
   ```
1. Download [pima.py](pima.py) and [pima_server.py](pima_server.py), and put them in the same directory.
1. Set run permissions to [pima_server.py](pima_server.py):
   ```bash
   chmod a+x pima_server.py
   ```
## Run
1. Test out that you can run the server, e.g.:
   ```bash
   ./pima_server.py --ssl_cert cert.pem --ssl_key key.pem --port 7777 --key my_random_key --login 000000 --zones 32
   ```
   Parameters:
   - `--ssl_cert` - Path to the SSL certificate file. If not set, will run a non-encrypted web server.
   - `--ssl_key` - Path to the SSL private key file. If not set, will get the key from the certificate file.
   - `--port` or `-p` - Port for the web server.
   - `--key` or `-k` - A key to authenticate the server calls.  
     Consider generating a random key using `uuidgen`.
   - `--login` or `-l` - The installer login code to the alarm.
   - `--zones` or `-z` - Number of zones supported by the alarm, one of 32, 96 or 144. Default is 32.
1. Access e.g. using curl:
   ```bash
   curl -i --cert ./cert.pem --key ./key.pem 'http://localhost:7777/pima?key=my_random_key&command=status'
   curl -i --cert ./cert.pem --key ./key.pem 'http://localhost:7777/pima?key=my_random_key&command=arm&mode=home1&partitions=1'
   ```
   CGI Arguments:
   - `key` - The key specified on the web server startup.
   - `command` - Either `status` or `arm`.  
      When `arm` is specified:
      - `mode` - Either `full_arm`, `home1`, `home2` or `disarm`.
      - `partitions` Comma separated list of partitions. Default is `1`.
## Automate
1. Create a dedicated directory for the script files, and move the files to it.
   Pass the ownership to root. e.g.:
   ```bash
   sudo mkdir /usr/lib/pima
   sudo mv pima_server.py pima.py key.pem cert.pem /usr/lib/pima
   sudo chown root:root /usr/lib/pima/*
   ```
1. Create a service configuration file (as root), e.g. `/lib/systemd/system/pima.service`:
   ```INI
   [Unit]
   Description=PIMA alarm server
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 -u pima_server.py --ssl_cert cert.pem --ssl_key key.pem --port 7777 --key my_random_key --login 000000 --zones 32
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
## Next steps
1. [Groovy](http://groovy-lang.org/) [Device Type Handlers](https://docs.smartthings.com/en/latest/device-type-developers-guide/) for [SmartThings](https://www.smartthings.com/) integration.
1. [MQTT](http://en.wikipedia.org/wiki/Mqtt) support using [Mosquitto](http://mosquitto.org/), for [HomeAssistant](https://www.home-assistant.io/) and [openHAB](https://www.openhab.org/) integration.
1. Support further functionality, e.g. change user codes.
