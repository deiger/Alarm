# PIMA Alarms

This program implements an interface for negotiation with PIMA Hunter Pro alarms.  
It was built based on PIMA's General Specification for Home Automation &
Building Management protocol Ver. 1.15.  
PIMA is a trademark of PIMA Electronic Systems Ltd, http://www.pima-alarms.com.  
This program was built with no affiliation of PIMA Electronic Systems Ltd.

## Prerequisites
1. PIMA Hunter Pro alarm, with 32, 96 or 144 zones.
1. PIMA Home Automation kit (SA-232, LCL-11A and Serial-to-USB cable).
1. Raspberry Pi or similar, connected to the alarm through the Home Automation kit.
1. Installer login code. It is not possible to connect to the alarm using a user login code.

## Setup
1. Create an SSL certificate, if you wish to access the server through HTTPS:
   ```bash
   openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365
   ```
1. Install additional Python libraries:
   ```bash
   pip3 install crcmod pyserial
   ```
1. Download `pima.py` and `pima_server.py`, and put them in the same directory.
1. Set run permissions to `pima_server.py`:
   ```bash
   chmod a+x pima_server.py
   ```
## Run
1. Run the server, e.g.:
   ```bash
   ./pima_server.py --ssl_cert cert.pem --ssl_key key.pem --port 7777 --key my_random_key --login 000000 --zones 32
   ```
   Parameters:
   - `--ssl_cert` - Path to the SSL certificate file. If not set, will run a non-encrypted web server.
   - `--ssl_key` - Path to the SSL private key file. If not set, will get the key from the certificate file.
   - `--port` or `-p` - Port for the web server.
   - `--key` or `-k` - Preferably random key to authenticate the server calls.
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
