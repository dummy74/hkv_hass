'''
Created on Dec 30, 2022

@author: holger
'''
from datetime import timedelta
from collections import OrderedDict
import logging

import async_timeout

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import DOMAIN
from .hub import HKVHub
from .hkv.packets import HKVTempDataPacket, HKVRelaisDataPacket
from dataclasses import asdict

_LOGGER = logging.getLogger(__name__)

class HKVCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""
    
    api: HKVHub

    def __init__(self, hass, dev:str, baud:int, interval:int):
        """Initialize my coordinator."""
        super().__init__(hass,_LOGGER,
                         name=DOMAIN,
                         # use push
                         #update_interval=timedelta(seconds=interval),
                         update_method=self.async_update_data,
                         )
        self.api = HKVHub(dev, baud)
        self.api.connect()
        self.api.hkv.register_packet_handler(self._handle_data_packet,HKVTempDataPacket)
        #self.api.hkv.register_packet_handler(self._handle_data_packet,HKVRelaisDataPacket)
        self.interval = interval
        
    @property
    def hkv(self):
        return self.api.hkv
        
    def _handle_data_packet(self,packet):
        self.logger.info(f"Handle HKV packet {packet}")
        
        dev_addr = packet.SRC
        data = asdict(packet)
        self.data['devices'][dev_addr].update(data)
        
        self.logger.info(f"Handle HKV packet data update {self.data=}")
        self.async_set_updated_data(self.data)
        

    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        self.logger.error("Fetching HKV data")
        #self.logger.debug(self.decodeInfo)

        if self.data is None:
            hub_data = OrderedDict(SRC=99,ID='HKV-Hub')
            self.data = {
                "hub": hub_data,
                "devices": OrderedDict()}
        
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(60):
                parsed_data =  await self.api.fetch_data()
            self.data.update(parsed_data)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

        return self.data
        
    def get_data(self):
        return self.data

    async def async_update_local_entry(self, dev_addr, key, value):
        data = self.data
        key = key.split('_')
        if len(key)==1:
            data["devices"][dev_addr][key[0]] = value
        else:
            data["devices"][dev_addr][key[0]][int(key[1])-1] = value
        self.logger.error(f"async_update_local_entry: {dev_addr=}, {key=} to {value}")
        self.logger.error(f"async_update_local_entry: {data=}")
        self.async_set_updated_data(data)
    
    # def set_value(self, dev_addr, key, keynum, value):
    #     if key.startswith('Relais'):
    #         self.logger.error(f"set_value: {dev_addr=}, {key=} ({keynum}) to {value}")
    #         self.api.hkv.set_relais((keynum,1 if value else 0),dst=dev_addr)
    
class HKVEntity(CoordinatorEntity, SensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

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
        """Turn the light on.

        Example method how to request data updates.
        """
        # Do the turning on.
        # ...

        # Update the data
        await self.coordinator.async_request_refresh()
        
        
        
