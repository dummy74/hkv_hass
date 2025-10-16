'''Created on Dec 30, 2022

@author: holger
'''
import asyncio
from collections import OrderedDict
from dataclasses import asdict
from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .hkv.packets import (
    HKVConnectionDataPacket,
    HKVRelaisDataPacket,
    HKVStatusDataPacket,
    HKVTempDataPacket,
)
from .hub import HKVHub

_LOGGER = logging.getLogger(__name__)

class HKVCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    api: HKVHub

    def __init__(self, hass, dev: str, baud: int, timeout: float, interval: int):
        """Initialize my coordinator."""
        super().__init__(hass, _LOGGER,
                         name=DOMAIN,
                         update_interval=timedelta(seconds=30),  # Reduziert auf 30s
                         update_method=self.async_update_data,
                         )
        self.api = HKVHub(dev, baud, timeout)
        # async with async_timeout(10):
        #     _LOGGER.info("Connecting ...")
        #     await self.api.connect()
        _LOGGER.debug("Start Connect Task ...")
        hass.async_create_task(self.api.connect())  # Async connect

        self.api.hkv.register_packet_handler(self._handle_data_packet, HKVTempDataPacket)
        self.api.hkv.register_packet_handler(self._handle_data_packet, HKVRelaisDataPacket)
        self.api.hkv.register_packet_handler(self._handle_data_packet, HKVStatusDataPacket)
        self.api.hkv.register_packet_handler(self._handle_data_packet, HKVConnectionDataPacket)
        self.interval = interval
        _LOGGER.debug("Coordinator finished Init")

    @property
    def hkv(self):
        """The HKV device."""
        return self.api.hkv

    async def _handle_data_packet(self, packet):
        _LOGGER.debug(f"Handle HKV packet {packet}")
        dev_addr = packet.SRC
        if dev_addr not in self.data['devices']:
            self.data['devices'][dev_addr] = OrderedDict(ID='UNKNOWN')  # Default
        data = asdict(packet)
        self.data['devices'][dev_addr].update({k: v for k, v in data.items() if k not in ['SRC', 'DST', 'TYPE']})
        _LOGGER.info(f"Handle HKV packet data update self.data['devices'][{dev_addr}]={self.data['devices'][dev_addr]}")
        self.async_set_updated_data(self.data)

    async def async_update_data(self):
        """Fetch data from API endpoint."""
        _LOGGER.info("Fetching HKV data")

        if self.data is None:
            hub_data = OrderedDict(SRC=99, ID='HKV-Hub')
            self.data = {
                "hub": hub_data,
                "devices": OrderedDict()}

        try:
            async with asyncio.timeout(90):
                while not self.api.connected:
                    await asyncio.sleep(1)
                parsed_data = await self.api.fetch_data(self.hass)
            self.data.update(parsed_data)
        except asyncio.CancelledError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

        return self.data

    def get_data(self):
        return self.data

    async def async_update_local_entry(self, dev_addr, key, value):
        data = self.data
        key_parts = key.rsplit('_', 1)
        if len(key_parts) == 2 and key_parts[-1].isnumeric():
            key = key_parts[0]
            index = int(key_parts[1]) #- 1
            data["devices"][dev_addr][key][index] = value
        else:
            data["devices"][dev_addr][key] = value
        _LOGGER.info(f"async_update_local_entry: {dev_addr=}, {key=} to {value}")
        _LOGGER.debug(f"async_update_local_entry: {data=}")
        self.async_set_updated_data(data)

class HKVEntity(CoordinatorEntity, SensorEntity):
    """An entity using CoordinatorEntity."""

    def __init__(self, coordinator, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self.idx = idx

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data[self.idx]["state"]
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        await self.coordinator.async_request_refresh()
