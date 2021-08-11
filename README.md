# Odo

![Odo Pi](https://github.com/Red-Team-Alliance/Odo/blob/main/docs/odo.jpg?raw=true)

## **Requirements**

- python3 (>= 3.9 for Lovense module)
- python3 venv module (some OS need to install it separately)
- MQTT broker (tested with mosquitto v2.0.10)

## **Setup**

- Setup python virtualenv

	`python3 -m venv .venv`

- Activate virtualenv

    `source .venv/bin/activate`

- Install requirements

    `pip install -r requirements.txt`

## **Running**

- Modify `config.yaml.sample` as needed and save as `config.yaml`

- Run `main.py`

    `python main.py`

Example minimal `config.yaml` with ESPKey, Proxmark3, & Lovense haptic feedback
```
---
modules:
  espkey:
  lovense:
  proxmark3:
```

# Module Information
## ESPKey

### Requirements

- Pi & ESPKey on same WiFi network.
- Recommend to configure Pi in AP mode with `hostapd` and connect ESPKey as client.

Defaults to `espkey.local` mDNS name for ESPKey host

`python -m espkey`

## Proxmark3 
### Requirements

- Proxmark3 client

### Setup

- Follow setup instructions from: https://github.com/RfidResearchGroup/proxmark3
- Compiled and `make install`. 
- Proxmark3 client wrapper `pm3` should be in your PATH and client should connect to Proxmark3 before attempting to run Odo

### Running individually

`python -m proxmark3`

## Waveshare Screen

Display captured credentials, status of components, change modes, & select a specific credential 

### Requirements

To run screen without `root`:
```
sudo setcap "cap_dac_override+ep cap_sys_rawio+ep" $(eval readlink -f `which node`)
```

- node >= v15 
- npm
- pigpio

### Setup

- `cd screen_ws13`
- `npm install`

### Running individually

- `cd screen_ws13`
- `node index.js`


# Contributing

See our contributers guide [here](docs/CONTRIBUTING.md)