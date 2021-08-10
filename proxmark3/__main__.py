import logging
from proxmark3 import Proxmark3

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s [%(threadName)s]',
)

if __name__ == "__main__":
    pm3 = Proxmark3()
    pm3.start()
    try:
        input("Press enter key to end")
    except KeyboardInterrupt:
        pass
    pm3.terminate()
    pm3.join()
