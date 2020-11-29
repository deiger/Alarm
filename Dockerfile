FROM python:3.9-alpine

ENV LOG_LEVEL "INFO"
ENV API_SSL_CERT ""
ENV API_SSL_KEY ""
ENV API_PORT 4693
ENV API_KEY ""
ENV PIMA_LOGIN ""
ENV PIMA_ZONES 32
ENV PIMA_SERIAL_PORT ""
ENV PIMA_HOST ""
ENV PIMA_PORT ""
ENV MQTT_HOST ""
ENV MQTT_PORT ""
ENV MQTT_CLIENT_ID "pima-server"
ENV MQTT_USER ""
ENV MQTT_PASSWORD ""
ENV MQTT_TOPIC "pima-server"
ENV API_MODE "Docker"

RUN apk update && \
    apk upgrade && \
    apk add --no-cache gcc libressl-dev musl-dev libffi-dev nano && \
    pip install flask pyopenssl crcmod pyserial paho-mqtt

COPY . /app/

EXPOSE 4693

ENTRYPOINT ["python3", "/app/entrypoint.py"]