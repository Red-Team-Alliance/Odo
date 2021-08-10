const { initialize, Gpio, terminate } = require('pigpio');
const EventEmitter = require('events');

const KEYS = {
  up:      6,
  down:    19,
  left:    5,
  right:   26,
  press:   13,
  1:        21,
  2:        20,
  3:        16,
}

process.on("SIGINT", () => {
  terminate();
});

class Controller extends EventEmitter {
  constructor() {
    super();
    initialize();
    Object.keys(KEYS).forEach(key => {
      const pin = KEYS[key];

      const button = new Gpio(pin, {
        mode: Gpio.INPUT,
        pullUpDown: Gpio.PUD_UP,
        alert: true
      });

      // Level must be stable for 10 ms before an alert event is emitted.
      button.glitchFilter(10000);

      button.on('alert', (level, tick) => {
        if (level === 0) {
          this.emit('button', key);
          this.emit(key);
          // Not sure about this
          if (this.key) {
            this[key]()
          }
        }
      });
    })
  }
}

module.exports = Controller
