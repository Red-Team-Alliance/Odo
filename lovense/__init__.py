from asyncio.exceptions import CancelledError
from time import sleep
import sys
import asyncio
import logging
import json
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from bleak import _logger as logger

service_uuid = "58300001-0023-4BD4-BBD5-A6920E4C5653"
tx_char_uuid = "58300002-0023-4BD4-BBD5-A6920E4C5653"
rx_char_uuid = "58300003-0023-4BD4-BBD5-A6920E4C5653"

from odo.models import BaseMqttDeviceModel
from .models import LovenseStateModel
from .patterns import *

class Lovense(BaseMqttDeviceModel):
    def __init__(self, events=event_patterns, default_pattern=foho, *args, **kwargs):
        super(Lovense, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger('odo.lovense.Lovense')
        self.event_loop = asyncio.new_event_loop()
        self.queue = asyncio.Queue()
        self.client = None
        self.restart = True
        self._event = None
        self.state = LovenseStateModel()
        self.event_patterns = event_patterns
        self.default_pattern = default_pattern
        self._subscribe_topics = [
            self.credential_topic["seen"],
            self.credential_topic["selected"],
            self.credential_topic["written"],
            self.command_topic
        ]

    """Overloads _send_state() to not call self.mqtt_client.loop()"""
    def _send_state(self):
        self.mqtt_client.publish(self.state_topic, self.state.to_json())

    def _handle_credential(self, msg=None):
        topic = msg.topic.split('/')
        pattern = self.default_pattern
        if topic == self.credential_topic['written']:
            message = json.loads(msg.payload)
            if "payload" in message:
                if "status" in message:
                    status = message["payload"]["status"]
                    pattern = self.event_patterns[topic[1]][status]
        if topic[1] in self.event_patterns:
            pattern = self.event_patterns[topic[1]]

        self.event_loop.create_task(self.vibe_pattern(pattern))

    def _handle_command(self, msg=None):
        # message = json.loads(msg.payload)
        self.logger.error(f"Command parsing not implemented")

    def _on_message(self, client, userdata, msg):
        self.logger.debug(f"MQTT message received-> {msg.topic} {str(msg.payload)}")
        if msg.topic in list(self.credential_topic.values()):
            self._handle_credential(msg=msg)

        if msg.topic == self.command_topic:
            self._handle_command(msg=msg)

    async def vibe_pattern(self, pattern):
        try:
            for vibe, duration in pattern:
                await self.write_cmd(vibe)
                sleep(duration)
        except Exception as e:
            self.logger.error(e)

    async def write_cmd(self, data):
        self.logger.debug(f"BLE Send: {data}")
        await self.queue.put(data)
        try:
            await self.client.write_gatt_char(tx_char_uuid,bytes(data, encoding="UTF-8"))
        except BleakError:
            self.state = LovenseStateModel()
            self._send_state()
            raise ConnectionError

    async def process_ble_response(self, response):
        cmd = await self.queue.get()

        if cmd.startswith("DeviceType"):
            values = response.split(':')
            self.logger.debug(f"Type: {values[0]} Version: {values[1]} MAC: {values[2]}")
            self.state.payload.device_type = values[0]
            self.state.payload.version = values[1]
            self.state.payload.mac_addr = values[2]
            self._send_state()

        elif cmd.startswith("GetBatch"):
            values = response.split(';')
            self.logger.debug(f"Batch: {values[0]}")
            self.state.payload.batch = values[0]
            self._send_state()

        elif cmd.startswith("Battery"):
            values = response.split(';')
            self.logger.debug(f"Battery: {values[0]}")
            self.state.payload.battery = int(values[0])
            self._send_state()

        elif cmd.startswith("Vibrate"):
            if response == "OK;":
                self.logger.debug("Response from vibrate")
            else:
                raise ValueError
        else:
            self.logger.debug(f"Unknown command: {cmd} and response: {response}")

    def ble_callback(self, sender: int, data: bytearray):
        response = data.decode(encoding="UTF-8")
        self.logger.debug(f"BLE Recv: {sender}: {response}")
        if response.endswith(";"):
            self.event_loop.create_task(self.process_ble_response(response))
    
    async def ble_disconnect(self):
        await self.client.stop_notify(rx_char_uuid)
        await self.client.disconnect()
        self._disconnect()

    async def connect_to_device(self, address):
        self.logger.info(f"Starting loop for {address}")
        async with BleakClient(address, loop=self.event_loop, timeout=30) as self.client:
            self.logger.info(f"Connecting to: {address}")
            self.state.payload.status = "connected"

            try:
                await self.client.start_notify(rx_char_uuid, self.ble_callback)
                await self.write_cmd("DeviceType;")
                await self.write_cmd("GetBatch;")
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(e)
                raise e

            self._send_state()
            self._event = asyncio.Event()

            await self._event.wait()

            await self.ble_disconnect()

        self.logger.info(f"Disconnect from: {address}")

    async def mqtt_loop(self):
        while True:
            if self.state.payload.status == "connected":
                self.mqtt_client.loop()
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(10)

    async def get_battery(self):
        while True:
            if (self.state.payload.status == "connected") and (self.state.payload.device_type is not None):
                await self.write_cmd("Battery;")
                await asyncio.sleep(10)
            else:
                await asyncio.sleep(1)
            

    async def scanner(self):
        while True:
            got_device = False
            tasks = []
            tasks.append(self.event_loop.create_task(self.mqtt_loop()))
            tasks.append(self.event_loop.create_task(self.get_battery()))
            try:
                devices = await BleakScanner.discover()
            except BleakError as e:
                self.logger.error(f"BLE Error: {e}")
                sys.exit(1)

            for d in devices:
                if str(d.name).startswith("LVS-"):
                    task = self.event_loop.create_task(self.connect_to_device(d))
                    tasks.append(task)
                    got_device = True

            if got_device:
                pass
            else:
                self.logger.info("No devices found, sleeping before next scan")
                for t in tasks:
                    self.logger.debug(f"Canceling: {t}")
                    t.cancel()
                for t in tasks:
                    try:
                        await t
                    except CancelledError:
                        self.logger.debug(f"Canceled: {t}")
                    finally:
                        await asyncio.sleep(3)
                if self.restart:
                    continue
                else:
                    break

            try:
                await asyncio.gather(*tasks)
            except ConnectionError:
                self.logger.error('Disconnected: cancelling all tasks')
                for t in tasks:
                    self.logger.debug(f"Canceling: {t}")
                    t.cancel()
                for t in tasks:
                    try:
                        await t
                    except CancelledError:
                        self.logger.debug(f"Canceled: {t}")
                    finally:
                        await asyncio.sleep(3)
            finally:
                await asyncio.sleep(5)
            if self.restart:
                self.logger.info('Restarting scan')
            else:
                self.logger.info('Exiting')
                break

    def _cleanup(self):
        self.restart = False
        if self._event is not None:
            self._event.set()

    def loop(self):
        self._send_state()
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_until_complete(self.scanner())
        self.event_loop.close()

