import pexpect
import sys
import json
import logging
from time import sleep
import re

from odo.models import BaseMqttDeviceModel
from proxmark3.models import Proxmark3StateModel
from espkey.models import ESPKeyCredential
from .helpers import escape_ansi

prox_regex = "^\[\=\]\sraw:\s*(.+)"

modes = {
    "auto": ["auto", "seen"],
    "seen": ["seen"],
    "selected": ["selected"]
}

class Proxmark3(BaseMqttDeviceModel):
    def __init__(self, port=None, client_timeout=10, client_retry=True, mode="seen", target="iclass", *args, **kwargs):
        super(Proxmark3, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger('odo.proxmark3.Proxmark3')
        self.port = port
        self.client = None
        self.client_timeout = client_timeout
        self.client_retry = client_retry
        self._retry_client = True
        self.state = Proxmark3StateModel(target=target)
        self._subscribe_topics = [
            self.credential_topic["seen"],
            self.credential_topic["selected"],
            self.command_topic
        ]

    def _create_client(self):
        command = 'pm3'
        if self.port is not None:
            command = f'pm3 -p {self.port}'
        client = pexpect.spawnu(command)
        while self._retry:
            self.logger.info(f"Starting client with command: {command}")
            try:
                index = client.expect('pm3 --> ', timeout=self.client_timeout)
            except pexpect.EOF:
                self.logger.error("Error: could not open client, got EOF")
                self._cleanup()
                sys.exit(1)
            except pexpect.TIMEOUT:
                if self.client_retry:
                    self.logger.error("Error: could not open client, got timeout, sleeping till retry")
                    sleep(10)
                    continue
            else:            
                if index == 0:
                    self.logger.info(f"Proxmark3 client connected")
                    self.state.payload.status = "connected"
                    self._send_state()                
                    return client
        

    @property
    def mode(self):
        return self.state.payload.mode

    @property
    def target(self):
        return self.state.payload.target
    
    def _change_mode(self, mode=None):
        if mode is not None:
            if mode != self.mode:
                if mode in modes.keys():
                    self.logger.debug(f"Changing mode from: {self.mode} to {mode}")
                    self.state.payload.mode = mode
                    self._send_state()
                else:
                    raise ValueError

    def _subscribe(self):
        for topic in self._subscribe_topics:
            self.mqtt_client.subscribe(topic)
    
    def _on_message(self, client, userdata, msg):
        self.logger.debug(f"Message received-> {msg.topic} {str(msg.payload)}")

        if msg.topic in list(self.credential_topic.values()):
            self._handle_credential(msg=msg)

        if msg.topic == self.command_topic:
            self._handle_command(msg=msg)
            

    def _handle_command(self, msg=None):
        message = json.loads(msg.payload)
        if message["type"] == "set":
            if "mode" in message["payload"]:
                self._change_mode(mode=message["payload"]["mode"])
            if "target" in message["payload"]:
                self.state.payload.target = message["payload"]["target"]
        else:
            self.logger.error("Command type not implemented")

    def _handle_credential(self, msg=None):
        process_credential = False
        topic = msg.topic.split('/')
        if topic[1] not in modes[self.mode]:
            self.logger.debug(f"Topic: {topic[1]} doesn't match mode: {self.mode}")
            if topic[1] == "selected":
                self._change_mode(mode="selected")
                process_credential = True
        else:
            self.logger.debug(f"Topic: {topic[1]} matches mode: {self.mode}")
            process_credential = True

        if process_credential:
            message = json.loads(msg.payload)
            if message["type"] == "wiegand":
                credential = ESPKeyCredential(payload=message["payload"])

                if self.target == "iclass":
                    self.encode_iclass(credential=credential)
                elif self.target == "prox":
                    self.encode_prox(credential=credential)
                else:
                    raise NotImplementedError

    def _send_command(self, command, result):
        self.client.sendline(command)
        try:
            index = self.client.expect(result)
        except pexpect.EOF:
            self.logger.error("Got EOF")
            self._cleanup()
            sys.exit(1)
        except pexpect.TIMEOUT:
            self.logger.error("Timeout waiting for response")
            self._cleanup()
            sys.exit(1)
        else:
            if index == 0:
                return escape_ansi(str(self.client.before))

    def encode_iclass(self, credential=ESPKeyCredential()):
        self.logger.info(f"{credential} Bin: {credential.to_binary()}")
        status_msg = json.loads(credential.to_json())
        status_msg["payload"]["status"] = "pending"
        self.mqtt_client.publish(self.credential_topic["written"], json.dumps(status_msg))
        self.mqtt_client.loop()

        command = f"hf iclass encode --bin {credential.to_binary()} --ki 0"
        self.logger.debug(f"-> {command}")
        resp = self._send_command(command, 'pm3 --> ')
        self.logger.debug(f"<- {resp}")
        status = [False, False, False]
        if "Write block 6/0x06 ( ok )".lower() in resp:
            status[0] = True

        if "Write block 7/0x07 ( ok )".lower() in resp:
            status[1] = True

        if "Write block 8/0x08 ( ok )".lower() in resp:
            status[2] = True

        if all(status):
            self.logger.info(f"Credential: {credential} Written successfully")
            status_msg["payload"]["status"] = "success"
        else:
            status_msg["payload"]["status"] = "failure"
            for i, state in enumerate(status):
                if state == False:
                    self.logger.error(f"Error writing block {i+6}")

        self.mqtt_client.publish(self.credential_topic["written"], json.dumps(status_msg))

    def encode_prox(self, credential=ESPKeyCredential()):
        preamble_cred = credential.to_hex(preamble=True)
        self.logger.info(f"{credential} Bin: {credential.to_binary()} Hex(w/ preamble): {preamble_cred}")
        status_msg = json.loads(credential.to_json())

        status_msg["payload"]["status"] = "pending"
        self.mqtt_client.publish(self.credential_topic["written"], json.dumps(status_msg))
        self.mqtt_client.loop()

        command = f"lf hid clone -r {preamble_cred}"
        self.logger.debug(f"-> {command}")
        resp = self._send_command(command, 'pm3 --> ')
        self.logger.debug(f"<- {resp}")

        # Check credential write
        command = f"lf hid reader"
        self.logger.debug(f"-> {command}")
        resp = self._send_command(command, 'pm3 --> ')
        self.logger.debug(f"<- {resp}")
        
        # Validate response
        match = re.search(prox_regex, resp, re.MULTILINE)
        if match:
            current_cred = match.group(1).lstrip('0')
            self.logger.debug(f"Target cred: {preamble_cred} Actual cred: {current_cred}")
            if preamble_cred == current_cred:
                self.logger.info(f"Credential: {credential} Written successfully")
                status_msg["payload"]["status"] = "success"
            else:
                self.logger.error(f"Target cred not cloned successfully")
                status_msg["payload"]["status"] = "failure"

        self.mqtt_client.publish(self.credential_topic["written"], json.dumps(status_msg))


    def _cleanup(self):
        if self.client:
            if self.client.isalive():
                self.client.sendline('quit')
                index = self.client.expect(pexpect.EOF)
                if index == 0:
                    self.logger.info("Proxmark3 client closed cleanly")

        if self.mqtt_client:
            self._disconnect()

    def loop(self):
        if self.client is None:
            self.client = self._create_client()

        while self.running:
            self.mqtt_client.loop()
