import paho.mqtt.client as mqtt
import json
import threading
import logging
from time import sleep

default_cred_topics = {
            "seen": "credentials/seen",
            "selected": "credentials/selected",
            "written": "credentials/written"
        }
class StatePayload(object):
    def __init__(self, status="disconnected", *args, **kwargs):
        self.status = status

class MqttApiModel(object):
    def __init__(self):
        self.version = 1
        self.type = None
        self.payload = None

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class StateModel(MqttApiModel):
    def __init__(self, payload=dict()):
        super(StateModel, self).__init__()
        self.version = 1
        self.type = "state"
        self.payload = StatePayload(**payload)

class BaseMqttDeviceModel(threading.Thread):
    def __init__(self, mqtt_host="localhost", cred_topics=default_cred_topics, mqtt_retry=True, *args, **kwargs):
        super(BaseMqttDeviceModel, self).__init__(*args, **kwargs)
        self.daemon = True
        self.logger = logging.getLogger('odo.BaseMqttDeviceModel')
        self.running = False
        self.state_topic = f"devices/{self.__module__.lower()}/state"
        self.command_topic = f"devices/{self.__module__.lower()}/cmd"
        self.credential_topic = cred_topics
        self.state = StateModel()
        self.mqtt_host = mqtt_host
        self.mqtt_retry = mqtt_retry
        self.mqtt_client = None
        self._subscribe_topics = [self.command_topic]
        self._retry = True

    def _subscribe(self):
        for topic in self._subscribe_topics:
            self.logger.debug(f"Subscribing to: {topic}")
            self.mqtt_client.subscribe(topic)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"Connected to MQTT Broker: {self.mqtt_host}")
        else:
            self.logger.error(f"Failed to connect, return code {rc}")
            raise(ConnectionError)
        self._subscribe()

    def _on_message(self, client, userdata, msg):
        self.logger.debug(f"MQTT Message received, but not handled")
        pass

    def _create_mqtt_client(self):
        c = mqtt.Client()
        c.on_connect = self._on_connect
        c.on_message = self._on_message
        got_client = False
        while self._retry:
            try:
                c.connect(self.mqtt_host)
                got_client = True
            except ConnectionRefusedError:
                if self.mqtt_retry:
                    self.logger.error("MQTT connection error, sleeping for 10 seconds")
                    sleep(10)
                    continue
            break

        if got_client:
            return c
        else:
            self.logger.debug("Not connected to MQTT and not retrying")
            return None

    def _send_state(self):
        self.mqtt_client.publish(self.state_topic, self.state.to_json())
        self.mqtt_client.loop()

    def _disconnect(self):
        self.state.payload.status = "disconnected"
        if self.mqtt_client:
            self._send_state()
            self.mqtt_client.disconnect()
        return

    def loop(self):
        raise NotImplementedError("Must override loop")

    def terminate(self):
        self._cleanup()
        self._retry = False
        self.running = False

    """Overload to cleanup connections when terminated"""
    def _cleanup(self):
        self._disconnect()
        pass

    def run(self):
        self.mqtt_client = self._create_mqtt_client()
        if self.mqtt_client:
            self.running = True
            self.loop()
