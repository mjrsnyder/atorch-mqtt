import argparse
import asyncio
import json
import paho.mqtt.client as mqtt
from bleak import BleakClient

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

class BLEPowerMeter:
  def __init__(self, address, callback):
    self._address = address
    self._packet = bytearray()
    self._client = None
    self._connected = False
    self._callback = callback

  async def connect_and_listen(self, uuid):
    async with BleakClient(self._address) as client:
      self._client = client
      self._connected = await self._client.is_connected()
      print("Connected %s" % self._connected)
      await self._client.start_notify(uuid, self.handle_data)
      self._client.set_disconnected_callback(self.handle_disconnect)
      print("Listening for updates")
      while await self._client.is_connected():
          await asyncio.sleep(2)

  async def disconnect(self):
    if await self._client.is_connected():
        await self._client.disconnect()

  def is_new_report(self, packet: bytearray):
    if packet.hex()[0:6] == "ff5501":
      return True
    else:
      return False

  def handle_disconnect(self, client):
    print("client disconnected")
    self._connected = False

  def handle_data(self, sender, data):
    # TODO: add a logger and make this stuff a debug log
    print("new data received")
    if self.is_new_report(data):
      self._packet = data
      print("new report received")
    else:
      print("last part of report received")
      self._packet = self._packet + data
      self.parse_data()

  def parse_data(self):
    # TODO: add a logger and make this a debug log
    print(self._packet.hex())

    # TODO: make this an object or something?
    metrics = {
      "voltage" : int.from_bytes(self._packet[4:7], 'big', signed=False) / 10.0,
      "amps" : int.from_bytes(self._packet[7:10], 'big', signed=False) / 1000.0,
      "amp_hours" : int.from_bytes(self._packet[10:13], 'big', signed=False) / 100.0,
      "kw_hours" : int.from_bytes(self._packet[13:17], 'big', signed=False) / 100.0,
      "cost" : int.from_bytes(self._packet[17:20], 'big', signed=False) / 100.0,
      # TODO: finish pulling the data from the packet
      "temp" :  int.from_bytes(self._packet[20:22], 'big', signed=False) # This is wrong...
    }
    self._callback(metrics)

def handle_metrics(metrics):
    mqtt_client.loop_write()
    mqtt_client.publish('solar-metrics', json.dumps(metrics))

async def run(args):
  mqtt_client.connect(args.mqtt_host)

  meter = BLEPowerMeter(args.address, handle_metrics)
  try:
    await meter.connect_and_listen(CHAR_UUID)
  finally:
    await meter.disconnect()

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-m", "--mqtt-host", help="The hostname or IP of the MQTT server to publish to", required=True)
  parser.add_argument("-a", "--address", help="The bluetooth address of your power monitor", required=True)
  args = parser.parse_args()

  mqtt_client = mqtt.Client()
  loop = asyncio.get_event_loop()

  loop.run_until_complete(run(args))

