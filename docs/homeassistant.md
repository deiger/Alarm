# PIMA2MQTT

## Setup MQTT Alarm and Sensors for Home Assistant

### Components
#### Alarm Control Panel
```yaml
alarm_control_panel:
  - platform: mqtt
    state_topic: "pima_alarm/status"
    command_topic: "pima_alarm/command"
    availability_topic: "pima_alarm/LWT"
    code_arm_required: false
    code_disarm_required: false
    value_template: >-
      {% if value_json['partitions']['1'] == 'home1' %}
        armed_home
      {% elif value_json['partitions']['1'] == 'full_arm' %}
        armed_away
      {% else %}
        disarmed
      {% endif %}
    payload_disarm: '{"mode": "disarm"}'
    payload_arm_home: '{"mode": "home1"}'
    payload_arm_away: '{"mode": "full_arm"}' 
```

#### Alarm Open Zones

```yaml
sensor:
  - name: "Alarm Open Zones"
    platform: mqtt
    state_topic: "pima_alarm/status"
    availability_topic: "pima_alarm/LWT"
    value_template: "{{ value_json['open zones'] }}"
```

#### Alarm Alarmed Zones
```yaml
sensor:
  - name: "Alarm Alarmed Zones"
    platform: mqtt
    state_topic: "pima_alarm/status"
    availability_topic: "pima_alarm/LWT"
    value_template: "{{ value_json['alarmed zones'] }}"
```

#### Alarm Arm State
```yaml
sensor:
  - name: "Alarm Arm State"
    platform: mqtt
    state_topic: "pima_alarm/status"
    availability_topic: "pima_alarm/LWT"
    value_template: "{{ value_json['partitions']['1'] }}"
```

### Lovelace
```yaml
cards:
  - entity: alarm_control_panel.mqtt_alarm
    name: PIMA Alarm
    states:
      - arm_home
      - arm_away
    type: alarm-panel
  - entities:
      - entity: sensor.alarm_arm_state
      - entity: sensor.alarm_open_zones
      - entity: sensor.alarm_alarmed_zones
    show_header_toggle: false
    type: entities
type: vertical-stack
```