import logging
import threading
import subprocess
import os

logging.getLogger('odo.screen')

class Screen(threading.Thread):
    def __init__(self, mqtt_host="localhost", pisugar2=False, *args, **kwargs):
        super(Screen, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger('odo.screen')
        self.process = None

    def _cleanup(self):
        self.logger.info("Screen client closed")

    def run(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.process = subprocess.Popen(["node", "index"], cwd=dir_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        #self.process.wait()

    def terminate(self):
        self._cleanup()
        if self.process is not None:
            self.process.terminate()

