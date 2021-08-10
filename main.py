#!/usr/bin/env python
import yaml
import logging
import sys

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger('odo.main')

from espkey import ESPKey
from proxmark3 import Proxmark3
from screen_ws13 import Screen
from lovense import Lovense

modules = []

try:
    with open('config.yaml','r') as file:
        config = yaml.safe_load(file)
except IOError:
    logger.error("No config file, see config.yaml.sample")
    sys.exit(1)

if __name__ == "__main__":
    for module in config['modules']:
        logger.info(f"{module} enabled.")
        mod_config = config['modules'][module]
        if mod_config:
            logger.debug(f"{module} config: {mod_config}")

    if "espkey" in config['modules']:
        mod_config = config['modules']['espkey']
        if mod_config:
            esp = ESPKey(**mod_config)
        else:
            esp = ESPKey()
        modules.append(esp)

    if "proxmark3" in config['modules']:
        mod_config = config['modules']['proxmark3']
        if mod_config:
            pm3 = Proxmark3(**mod_config)
        else:
            pm3 = Proxmark3()
        modules.append(pm3)
    
    if "screen_ws13" in config['modules']:
        mod_config = config['modules']['screen_ws13']
        if mod_config:
            ws13 = Screen(**mod_config)
        else:
            ws13 = Screen()
        modules.append(ws13)

    if "lovense" in config['modules']:
        mod_config = config['modules']['lovense']
        if mod_config:
            lvs = Lovense(**mod_config)
        else:
            lvs = Lovense()
        modules.append(lvs)

    for module in modules:
        logger.info(f"Starting: {module}")
        module.start()

    try:
        input("Press enter or Ctrl + c to end")
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Received signal, exiting")
        
    for module in modules:
        logger.info(f"Stopping: {module}")
        module.terminate()
        module.join()
