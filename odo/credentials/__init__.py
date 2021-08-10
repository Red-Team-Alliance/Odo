import json
from odo.models import MqttApiModel
class WiegandPayload(object):
    def __init__(self, bits=None, hex=None):
        self.bits = bits
        self.hex = hex

class WiegandCredential(MqttApiModel):
    def __init__(self, payload=dict(), *args, **kwargs):
        super(WiegandCredential, self).__init__(*args, **kwargs)
        self.version = 1
        self.type = "wiegand"
        self.payload = WiegandPayload(**payload)
    
    def to_binary(self):
        return bin(int(self.payload.hex, 16))[2:].zfill(int(self.payload.bits))

    def __str__(self):
        return f"Bits: {self.payload.bits} Hex: {self.payload.hex}"