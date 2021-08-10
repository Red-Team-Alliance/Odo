const fs = require("fs");
const { spawn } = require("child_process");
const WebSocket = require("ws");
const mqtt = require('mqtt')
const LCD = require("@bettse/ws13lcd");
const YAML = require('yaml')
const Controller = require("./Controller");

const { Colors } = LCD;
const { BLACK, WHITE, RED, GREEN, BLUE, MAGENTA, CYAN, YELLOW, GRAY } = Colors;
const logError = err => err && log.err(err);

const EMPTY = 0
const FILL = 1

const DECIMAL = 10;
const font = { xs: 8, sm: 12, md: 16, lg: 20, xl: 24 };
const speed = {
  hyper: 100,
  fast: 300,
  slow: 1000,
  snail: 5000,
}

const fontRatio = {
  [font.xs]: 5,
  [font.sm]: 7,
  [font.md]: 11,
  [font.lg]: 14,
  [font.xl]: 17,
}

const SCREEN = {
  HEIGHT: LCD.HEIGHT - font.xl,
  WIDTH: LCD.WIDTH - fontRatio[font.xl],
}

const aliases = [
  'Alice', 'Bob', 'Carol', 'Dan', 'Eve',
  'Faythe', 'Grace', 'Heidi', 'Ivan', 'Judy',
  'Karl', 'Lex', 'Mallory', 'Nate', 'Olivia',
  'Pat', 'Quinn', 'Rupert', 'Sybil',
  'Trent', 'Ursula', 'Vanna', 'Walter',
  'Xander', 'Yennefer', 'Zee',
]
var alias_index = 0;
var showAlias = false;

process.on("SIGINT", () => {
  console.log('SIGINT');
  LCD.clear(BLACK);
  LCD.exit();
  process.exit();
});

var charging = false;
var percent = 0;
var proxmark = {
  status: 'disconnected',
  mode: ''
}
var espkey = {
  status: 'disconnected',
}

function drawText(x, y, s, f = font.md, fore = WHITE, back = BLACK) {
  LCD.drawString(x, y, s, f, fore, back);
}

/*
// If you want labels to line up with buttons on the right:
drawTextRightJustify(40 + font.xl/2, "one-", font.xl, RED)
drawTextRightJustify(100 + font.xl/2, "two-", font.xl, RED)
drawTextRightJustify(160 + font.xl/2, "three-", font.xl, RED)
*/

function drawTextRightJustify(y, s, f = font.md, fore = WHITE, back = BLACK) {
  const charWidth = fontRatio[f];
  const x = LCD.WIDTH - charWidth * s.length;
  drawText(x, y, s, f, fore, back)
}

function str2Const(str) {
  const map = {
    'black': BLACK,
    'white': WHITE,
    'red': RED,
    'green': GREEN,
    'blue': BLUE,
    'magenta': MAGENTA,
    'cyan': CYAN,
    'yellow': YELLOW,
    'gray': GRAY,
  }
  return map[str.toLowerCase()] || WHITE;
}

function displayCredentials(credentials, selected) {
  const fontSize = font.lg;
  const maxChar = Math.floor(SCREEN.WIDTH / fontRatio[fontSize]) - 1; // -1 to accomidate status indicator
  const x = 0;
  const maxLines = Math.floor(SCREEN.HEIGHT / fontSize);
  let start = 0;
  let end = maxLines; // The end line isn't shown

  if (selected >= end) {
    start = selected - end + 1;
    end = start + maxLines;
  }
  // console.log({maxLines, start, selected, end});

  LCD.draw(() => {
    LCD.clear(BLACK);

    drawStatusLine();

    drawTextRightJustify(40 + font.xl/2, 'A', font.xl, (proxmark.mode === 'auto' ? WHITE : GRAY));
    drawTextRightJustify(100 + font.xl/2, 'S', font.xl, (proxmark.mode === 'selected' ? WHITE : GRAY));
    drawTextRightJustify(160 + font.xl/2, 'N', font.xl, (showAlias ? WHITE : GRAY));

    if (credentials.length === 0) {
      return;
    }

    if (start > 0) {
      drawTextRightJustify(0, start.toString(), font.md, RED);
    }
    if (end < credentials.length) {
      drawTextRightJustify(SCREEN.HEIGHT - font.md, (credentials.length - end).toString(), font.md, RED);
    }

    const statusMap = {
      'pending': GRAY,
      'success': GREEN,
      'failure': RED,
    }

    //console.log({credentials})
    credentials.slice(start, end).forEach((credential, i) => {
      try {
        const { alias, hex, status } = credential
        const y = i * fontSize;
        const display = showAlias ? alias : `${hex.substring(0, maxChar)}`
        const invert = (start + i) === selected;
        const fore = invert ? BLACK : WHITE;
        const back = invert ? GRAY : BLACK;

        // console.log({x, y, display, fontSize, invert, fore, back})
        drawText(x, y, display, fontSize, fore, back);

        if (statusMap[status]) {
          LCD.drawCircle(x + fontRatio[fontSize] * (display.length + 1), y + fontSize/2, fontSize/2 - 1, statusMap[status]);
        }
      } catch (e) {
        console.log('error rendering credential', e);
      }
    });
  });
}

function drawStatusLine() {
  const charWidth = fontRatio[font.xl];
  const proxStatus = proxmark.status === 'connected' ? 'PM3' : '   '
  const espStatus = espkey.status === 'connected' ? 'ESP' : '   '

  drawText(0, SCREEN.HEIGHT, proxStatus, font.xl, RED);
  drawText(charWidth * proxStatus.length, SCREEN.HEIGHT, espStatus, font.xl, BLUE);

  drawTextRightJustify(SCREEN.HEIGHT, `${charging ? '+' : ''} ${percent}%`, font.xl, percent < 50 ? RED : WHITE);
}

function batteryMonitor() {
  const ws = new WebSocket("ws://localhost:8421/ws");

  ws.on("open", function open() {
    ws.send("get battery");
  });

  ws.on("message", function incoming(data) {
    if (data.startsWith("battery: ")) {
      percent = parseInt(data.slice("battery: ".length), DECIMAL);
    } else if (data.startsWith("battery_power_plugged: ")) {
      charging = JSON.parse(data.slice("battery_power_plugged: ".length));
    } else if (data.length > 0) {
      log.err("WS message:", data);
    }
    // drawStatusLine();
  });

  setInterval(() => {
    ws.send("get battery");
    ws.send("get battery_power_plugged");
  }, speed.slow);
}

function main() {
  var config = {
    pisugar2: false,
    mqtt_host: 'localhost'
  }
  try {
    fs.accessSync('../config.yaml'); // throws on failure
    const configYaml = fs.readFileSync('../config.yaml', 'utf8')
    const full_config = YAML.parse(configYaml)
    const { modules } = full_config
    const { screen_ws13 } = modules;
    config = screen_ws13
    console.log({config})
  } catch(e) {
    console.log('Error accessing or parsing config, using defaults');
  }
  const { pisugar2, mqtt_host } = config;

  const controller = new Controller();
  const client  = mqtt.connect({host: mqtt_host});

  client.on('message', function (topic, buffer) {
    try {
      const message = JSON.parse(buffer.toString());
      // console.log({topic, message})
      const { version } = message;
      if (version === undefined || message.version < 1) {
        console.log('discarding message with version less than 1');
        return;
      }
      switch(topic) {
        case 'credentials/seen':
          const index = credentials.findIndex((credential) => {
            return credential.hex === message.payload.hex;
          })
          if (index === -1) {
            credentials.push({
              type: message.type,
              hex: message.payload.hex,
              bits: message.payload.bits,
              timestamps: [message.payload.timestamp],
              alias: alias_index < aliases.length ? aliases[alias_index] : message.payload.hex,
            })
            alias_index++;
          } else {
            credentials[index].timestamps.push(message.payload.timestamp);
          }

          credentials.sort((a, b) => {
            return Math.max(...b.timestamps) - Math.max(...a.timestamps);
          })

          break;
        case 'credentials/written':
          // TODO: track status per-timestamp
          const update = credentials.findIndex((credential) => {
            return credential.hex === message.payload.hex;
          })
          if (update > -1) {
            credentials[update].status = message.payload.status;
          } else {
            console.log('unknown credential', message)
          }
          break;
        case 'devices/proxmark3/state':
          proxmark = message.payload
          break;
        case 'devices/espkey/state':
          espkey.status = message.payload.status;
          break;
        default:
          console.log('Message on topic', topic);
      }
      displayCredentials(credentials, selected);
    } catch (e) {
      console.log('error parsing mqtt message', e);
    }
  });
  client.on('connect', function () {
    client.subscribe('credentials/seen', logError);
    client.subscribe('credentials/written', logError);
    client.subscribe('devices/proxmark3/state', logError);
    client.subscribe('devices/espkey/state', logError);
  })


  let updating = null;
  let selected = 0;
  let credentials = [];
  /*
   * [
   * {
   *  type: 'wiegand',
   *  hex: '',
   *  bits: '',
   *  timestamps: []
   * }
   * ]
   */

  LCD.init();
  LCD.clear(BLACK);

  if(pisugar2) {
    batteryMonitor();
  }

  controller.on("up", () => {
    selected = (selected - 1 + credentials.length) % credentials.length
    displayCredentials(credentials, selected);
  });

  controller.on("down", () => {
    selected = (selected + 1 + credentials.length) % credentials.length
    displayCredentials(credentials, selected);
  });

  controller.on("press", () => {
    const credential = credentials[selected];
    if (!credential) {
      return;
    }
    const { type, hex, bits, timestamps } = credential;
    const event = {
      version: 1,
      type,
      payload: {
        bits,
        hex,
        timestamp: Math.max(timestamps),
      },
    }
    client.publish('credentials/selected', JSON.stringify(event));
  });

  controller.on("left", () => {});

  controller.on("right", () => {});

  controller.on("1", async () => {
    const command = {
      version: 1,
      type: 'set',
      payload: {
        mode: 'auto',
      },
    }
    client.publish('devices/proxmark3/cmd', JSON.stringify(command));
  });

  controller.on("2", async () => {
    const command = {
      version: 1,
      type: 'set',
      payload: {
        mode: 'selected',
      },
    }
    client.publish('devices/proxmark3/cmd', JSON.stringify(command));
  });

  controller.on("3", async () => {
    showAlias = !showAlias;
  });

  updating = setInterval(() => {
    displayCredentials(credentials, selected);
  }, speed.fast);
  displayCredentials(credentials, selected);
}

main()
