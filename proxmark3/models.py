from odo.models import StateModel

class Proxmark3StatePayload(object):
    def __init__(self, status="disconnected", mode="auto", target="iclass", *args, **kwargs):
        self.status = status
        self.mode = mode
        self.target = target

class Proxmark3StateModel(StateModel):
    def __init__(self, payload=dict(), *args, **kwargs):
        super(Proxmark3StateModel, self).__init__(*args, **kwargs)
        self.payload = Proxmark3StatePayload(**payload)
