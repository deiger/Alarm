# PIMA2MQTT

This program implements an interface for negotiation with [PIMA Hunter Pro alarms](https://www.pima-alarms.com/our-products/hunter-pro-series/).  
It was built based on PIMA&trade;'s General Specification for Home Automation &
Building Management protocol Ver. 1.15.  
PIMA&trade; is a trademark of PIMA Electronic Systems Ltd, http://www.pima-alarms.com.  
This program was built with no affiliation of PIMA Electronic Systems Ltd.

## Prerequisites
1. PIMA Hunter Pro alarm&trade;, with 32, 96 or 144 zones.
1. PIMA Home Automation kit&trade; (`SA-232`, `LCL-11A` and Serial-to-USB cable), or `net4pro` ethernet connection.
   Diagram by PIMA&trade; &copy;:
   ![Diagram by PIMA&trade; &copy;](docs/home_automation_kit.png)
   - According to various users, the alarm can be alternatively connected using a `PL2303TA` USB-to-TTL cable, like [this one](https://www.aliexpress.com/item/32345829369.html).
   - Yet another option is to connect directly to Raspberry pi, as specified here:
   ![Diagram by @maorcc](docs/rpi_connection.png)
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

## How to run

- [Command Line](docs/command_line.md)
- [Docker](docs/docker.md)
- [Home Assistant](docs/homeassistant.md)

## MQTT

#### Publishes

##### Status: pima_alarm/status
```json
{
  "partitions": {
    "1": "home1"
  },
  "open zones": [],
  "alarmed zone": [],
  "bypassed zones": [],
  "failed zones": [],
  "failures": []
}
```

##### Last Will and Testament: pima_alarm/LWT
- online
- offline

#### Subscribes

##### pima_alarm/arm
Each of the following commands can receive which partitions to execute the command,
By default `partitions: [ "1" ]`


Arm
```json
{
  "mode": "full_arm"
}
```

Arm Home1
```json
{
  "mode": "home1"
}
```

Arm Home2
```json
{
  "mode": "home2"
}
```

Disarm
```json
{
  "mode": "disarm"
}
```

## Web Server endpoints

Each request to the server must include in the URL (query string) the api_key, e.g. ```/pima/status?api_key=test```

#### GET /pima/status
Returns status

##### Http Codes

Code | Reason | Description
--- | --- | --- |
200 | OK | Set arm state changed successfully
401 | Unauthorized request | api_key doesn't match to the defined key


#### POST /pima/arm
##### Body
Name | Type | Required | Default | Description
--- | --- | --- | --- | --- |
mode | str | True | None | Which command to run, supported options - arm, disarm, home1, home2
partitions | array of int | False | `[ "1" ]` | Which partition to use, accept array of int

Returns status

##### Http Codes

Code | Reason | Description
--- | --- | --- |
200 | OK | Set arm state changed successfully
400 | Invalid request data | Empty payload sent within the request
401 | Unauthorized request | api_key doesn't match to the defined key
501 | Invalid arm mode, must be one of `full_arm`, `home1`, `home2`, `disarm` | received mode is not supported


## Next steps
1. [Groovy](http://groovy-lang.org/) [Device Type Handlers](https://docs.smartthings.com/en/latest/device-type-developers-guide/) for [SmartThings](https://www.smartthings.com/) integration.
1. Support further functionality, e.g. change user codes.
