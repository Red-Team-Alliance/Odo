import requests
import sys
import re
from time import sleep
import logging

logging.getLogger('odo.espkey')
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

from odo.models import BaseMqttDeviceModel
from .models import ESPKeyStateModel, ESPKeyCredential

class ESPKey(BaseMqttDeviceModel):
    def __init__(self, url="http://espkey.local/", log="log.txt", poll_interval=1, *args, **kwargs):
        super(ESPKey, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger('odo.espkey.ESPKey')
        self.url = url
        self.logfile = log
        self.session = None
        self.session_retry = True
        self.poll_interval = poll_interval
        self.state = ESPKeyStateModel()
        self.credentials = []
        self.latest_credential = ESPKeyCredential()
    
    def _create_session(self):
        s = requests.Session()
        got_session = False
        while self.session_retry:
            try:
                resp = s.get(self.url + 'version', timeout=5)
                got_session = True
            except requests.exceptions.ConnectionError:
                self.logger.error("Could not establish session with ESPKey, sleeping for 10 seconds")
                sleep(10)
                continue
                
            if resp.status_code != 200:
                self.logger.error(f"Invalid response code: {resp.status_code} to request for /version")
                continue
            else:
                self.session_retry = False

        if got_session:   
            self.state = ESPKeyStateModel(payload=resp.json()) 
            self.state.payload.status = "connected"
            self.logger.info(f"ESPKey Connected. Version: {self.state.to_json()}")
            self._send_state()
            return s
        else:
            self.logger.error("Could not get session and not retrying")
            sys.exit(1)

    def get_log(self):
        if self.session is None:
            self.logger.debug("No session found, creating one")
            self.session = self._create_session()
        logurl = self.url + self.logfile
        resp = self.session.get(logurl)
        if resp.status_code != 200:
            self.logger.error("Error fetching logfile")
            return False
        return resp

    def get_pacs_data(self):
        carddata = re.compile(r'^(\d*)\s(\w*):(\d*)')
        logdata = self.get_log()
        got_new_credential = False
        credential = None
        for line in logdata.iter_lines():
            card = carddata.match(line.decode('utf-8'))
            if card:
                if card.group(1) in self.credentials:
                    continue
                else:
                    got_new_credential = True
                    credential = ESPKeyCredential(payload={
                        "bits": int(card.group(3)),
                        "hex": card.group(2),
                        "timestamp": int(card.group(1))
                    })
        
                    self.logger.info(f"New credential from log: {credential}")
                    self.credentials.append(card.group(1))
                    
        if credential.payload.hex == self.latest_credential.payload.hex:
            self.logger.info(f"Repeat credential: {card.group(2)}")
            got_new_credential = False
        else:
            self.latest_credential = credential
        
        return got_new_credential, credential

    def _cleanup(self):
        self._disconnect()
        self.logger.info("ESPKey client closed")

    def loop(self):
        while self.running:
            got_credential, credential = self.get_pacs_data()
            if got_credential:
                self.logger.debug(f"Publish -> {credential.to_json()}")
                self.mqtt_client.publish(self.credential_topic["seen"], credential.to_json())
            else:
                sleep(self.poll_interval)

            self.mqtt_client.loop()
