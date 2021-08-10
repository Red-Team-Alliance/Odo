from odo.models import StateModel

class LovenseStatePayload(object):
    def __init__(self, status="disconnected", device_type=None, version=None, mac_addr=None, batch=None, battery=0, *args, **kwargs):
        self.device_type = device_type
        self.version = version
        self.mac_addr = mac_addr
        self.batch = batch
        self.battery = battery
        self.status = status

class LovenseStateModel(StateModel):
    def __init__(self, payload=dict(), *args, **kwargs):
        super(LovenseStateModel, self).__init__(*args, **kwargs)
        self.payload = LovenseStatePayload(**payload)
