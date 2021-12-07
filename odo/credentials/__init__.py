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

    def to_bytes(self):
        num = self.bits / 8
        if self.bits % 8:
            num += 1
        return int(self.payload.hex, 16).to_bytes(num, 'big')

    def to_hex(self, preamble=False):
        if preamble:
            return self._prox_preamble()
        else:
            return self.payload.hex()

    def _prox_preamble(self):
        t = int()
        bitnum = self.payloaad.bits

        if bitnum < 37:
            t = 1 << 37
            t = t | 1 << bitnum

        for bit in self.to_binary():
            bitnum = bitnum - 1
            if bit == '1':
                t = t | 1 << bitnum
            else:
                t = t | 0 << bitnum

        return hex(t)[2:]

    def __str__(self):
        return f"Bits: {self.payload.bits} Hex: {self.payload.hex}"