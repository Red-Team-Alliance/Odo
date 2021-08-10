import logging
from espkey import ESPKey

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s [%(threadName)s]',
)

if __name__ == "__main__":
    esp = ESPKey()
    esp.start()
    try:
        input("Press enter key to end")
    except KeyboardInterrupt:
        pass
    esp.terminate()
    esp.join()
