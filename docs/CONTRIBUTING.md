# Contributing

Submit PRs to fix bugs and add new modules!

## **Mock ESPKey**

- Create a web directory: `mkdir www && cd www`
- Create a log.txt  `echo '39399 20a7456:26' > log.txt`
- Create a version  `echo '{"version": "131", "log_name": "Alpha", "ChipID": "fake"}' > version`
- Host webserver    `python3 -m http.server`
- Reconfigure `config.yaml` ESPKey url to `http://localhost:8000/`


To simulate credential read events just append credential data to `log.txt` with new timestamped entries. Use `watch` to automate: `watch -n30 'echo "$(date +%s) 20a7457:26" >> www/log.txt'`

