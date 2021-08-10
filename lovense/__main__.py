import logging
from lovense import Lovense

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s [%(threadName)s]',
)

if __name__ == "__main__":
    vibe = Lovense()
    vibe.start()
    try:
        input("Press enter key to end")
    except KeyboardInterrupt:
        pass
    vibe.terminate()
    vibe.join()
