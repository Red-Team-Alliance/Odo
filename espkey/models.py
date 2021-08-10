from odo.models import StateModel
from odo.credentials import WiegandCredential, WiegandPayload

class ESPKeyStatePayload(object):
    def __init__(self, status="disconnected", version=None, ChipID=None, *args, **kwargs):
        self.version = version
        self.ChipID = ChipID
        self.status = status

class ESPKeyStateModel(StateModel):
    def __init__(self, payload=dict(), *args, **kwargs):
        super(ESPKeyStateModel, self).__init__(*args, **kwargs)
        self.payload = ESPKeyStatePayload(**payload)

class ESPKeyPayload(WiegandPayload):
    def __init__(self, bits=None, hex=None, timestamp=None, *args, **kwargs):
        self.bits = bits
        self.hex = hex
        self.timestamp = timestamp

class ESPKeyCredential(WiegandCredential):
    def __init__(self, payload=dict(), *args, **kwargs):
        super(ESPKeyCredential, self).__init__(*args, **kwargs)
        self.payload = ESPKeyPayload(**payload)

