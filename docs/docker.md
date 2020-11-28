# PIMA2MQTT

## Setup as Docker

### Environment Variables

Name | Type | Required | Default | Description
--- | --- | --- | --- | --- |
LOG_LEVEL | str | True | INFO | Minimal log level
API_SSL_CERT | str | False | None | Path to SSL certificate file
API_SSL_KEY | str | False | None | Path to SSL key file 
API_PORT | int | True | 4693 | Port for the server  
API_KEY | str | True | None | URL key to authenticate calls
PIMA_LOGIN | str | True | None | Login code to the PIMA alarm
PIMA_ZONES | int | True | 32 | Alarm supported zones, supported values - 32, 96, 144
PIMA_SERIAL_PORT | str | False | None | Serial port, e.g. /dev/serial0. Needed if connected directly through GPIO serial
PIMA_HOST | str | False | None | Pima alarm hostname or IP address. if connected by ethernet (net4pro)
PIMA_PORT | int | False | None | Pima alarm port. if connected by ethernet (net4pro)
MQTT_HOST | str | False | None | MQTT broker hostname or IP address
MQTT_PORT | int | False | None | MQTT broker port
MQTT_CLIENT_ID | str | False | pima-server | MQTT client id
MQTT_USERNAME | str | False | None | MQTT username
MQTT_PASSWORD | str | False | None | MQTT password
MQTT_TOPIC | str | False | pima_server | MQTT topic

### Compose

```yaml
version: '2'
services:
  pima2mqtt:
    image: "eladbar/pima2mqtt:latest"
    container_name: "pima2mqtt"
    hostname: "pima2mqtt"
    restart: unless-stopped
    ports:
      - 4693:4693
    environment:
      - LOG_LEVEL=DEBUG
      - API_SSL_CERT=/ssl/ssl.cert
      - API_SSL_KEY=/ssl/ssl.key
      - API_PORT=4693
      - API_KEY=SecretKey
      - PIMA_LOGIN=123456
      - PIMA_ZONES=32
      - PIMA_SERIAL_PORT=/dev/serial/by-path # Relevant for SA-232, LCL-11A and Serial-to-USB cable only
      - PIMA_HOST=127.0.0.1 # Relevant for net4pro only
      - PIMA_PORT=123456 # Relevant for net4pro only
      - MQTT_HOST=127.0.0.1
      - MQTT_PORT=1883
      - MQTT_CLIENT_ID=pima-server
      - MQTT_USER=user
      - MQTT_PASSWORD=pass
      - MQTT_TOPIC=pima_server
    volumes:
      - /ssl/ssl.key:/ssl/ssl.key:ro
      - /ssl/ssl.cert:/ssl/ssl.cert:ro
```
