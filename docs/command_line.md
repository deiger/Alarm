# PIMA2MQTT

## Setup as Command Line

### Setup
1. Create an SSL certificate, if you wish to access the server through HTTPS:
   ```bash
   openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
   ```
1. Install additional Python libraries:
   ```bash
   pip3 install flask pyopenssl crcmod paho-mqtt pyserial
   ```
1. Download files, and put them in the same directory.
1. Set run permissions to [entrypoint.py](entrypoint.py):
   ```bash
   chmod a+x entrypoint.py
   ```

### Run for testing
Test out that you can run the server, e.g.:
```bash
./pima_server.py --ssl_cert cert.pem --ssl_key key.pem --port 7777 --key my_random_key --login 000000 --mqtt_host localhost
```

### Arguments

Name | Type | Required | Default | Description
--- | --- | --- | --- | --- |
--log_level | str | True | INFO | Minimal log level
--ssl_cert | str | False | None | Path to SSL certificate file
--ssl_key | str | False | None | Path to SSL key file 
-p / --port | int | True | 4693 | Port for the server  
-k / --key | str | True | None | URL key to authenticate calls
-l / --login | str | True | None | Login code to the PIMA alarm
-z / --zones | int | True | 32 | Alarm supported zones, supported values - 32, 96, 144
--serialport | str | False | None | Serial port, e.g. /dev/serial0. Needed if connected directly through GPIO serial
--pima_host | str | False | None | Pima alarm hostname or IP address. if connected by ethernet (net4pro)
--pima_port | int | False | None | Pima alarm port. if connected by ethernet (net4pro)
--mqtt_host | str | False | None | MQTT broker hostname or IP address
--mqtt_port | int | False | None | MQTT broker port
--mqtt_client_id | str | False | pima-server | MQTT client id
--mqtt_user | str | False | None | `<username:password>` for the MQTT channel
--mqtt_topic | str | False | pima_server | MQTT topic

### Run as a service
1. Create a dedicated directory for the script files, and move the files to it.
   Pass the ownership to root. e.g.:
   ```bash
   sudo mkdir /usr/lib/pima
   sudo mv pima_server.py pima.py key.pem cert.pem /usr/lib/pima
   sudo chown root:root /usr/lib/pima/*
   sudo pip3 install flask pyopenssl crcmod paho-mqtt pyserial
   ```
1. Create a service configuration file (as root), e.g. `/lib/systemd/system/pima.service`:
   ```INI
   [Unit]
   Description=PIMA alarm server
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 -u endpoint.py --ssl_cert cert.pem --ssl_key key.pem --port 7777 --key my_random_key --login 000000 --mqtt_host localhost
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