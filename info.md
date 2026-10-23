# Teknix ESPRO-15 Local — Serhii fork

Maintained fork for the tested **Teknix ESPRO-15 with six 2.5 kW stages**. Not for ESPRO-12 or unverified revisions. Local MQTT control, no Teknix cloud account required. Based on Vitalii Kovalenko's upstream v0.1.2; MIT license retained.

## Features

- Native **climate entity** for thermostat-style control
- Live sensors: room / coolant / DHW temperatures, error code; separate rated-power diagnostic (not live consumption)
- Number controls: heating setpoint, room setpoint, DHW setpoint, power level, hysteresis, safety limits
- Switches: main switch (boiler on/off), heating on/off, DHW on/off
- Select: heating mode (by coolant/air)
- P4/P5 power stages: 2.5, 5, 7.5, 10, 12.5, 15 kW; P6 display corrected
- Telemetry unavailable after more than 90 seconds without a valid INFO frame; checked every 10 seconds
- Services: `set_field` (write any INFO field) and `send_raw` (advanced debugging)
- English and Ukrainian translations

## How it works

The boiler's Wi-Fi module runs Tasmota internally and talks to the MCU over UART. The integration:

1. Subscribes to the Tasmota serial topic via MQTT
2. Parses the boiler's `I0&...Z` / `I1&...Z` status frame into ~45 named fields
3. Configures Tasmota rules for 30s INFO polling automatically
4. Sends T-prefix write commands (with checksum) to change settings
5. Uses `Backlog` to refresh state within ~1 second of any change

## Prerequisite

**Your boiler's Wi-Fi module must already be connected to your local MQTT broker** (not `api.teknix.pro`). This is a one-time reconfiguration — see the full README for step-by-step instructions. Switching to local MQTT also means the Teknix mobile app stops working, because the Tasmota module can only connect to one broker at a time.

## Requirements

- Tested ESPRO-15 (six 2.5 kW stages) with stock Wi-Fi module
- MQTT integration configured in Home Assistant and connected to the same broker as the boiler
- Home Assistant 2024.4.0+

## Setup

After installation, add via Settings → Devices & Services → Add Integration → "Teknix ESPRO Boiler Local". Enter your Tasmota topic (e.g. `boiler_kotel`) and the integration handles the rest.

See the [README](https://github.com/mrSerhii88/teknix-espro-local) and [fork maintenance/migration guide](https://github.com/mrSerhii88/teknix-espro-local/blob/main/docs/FORK.md). Domain and entity keys are unchanged. The watchdog does not replace hardware protection or guarantee that an offline boiler can be stopped remotely.
