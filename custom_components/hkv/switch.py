"""Support for victron energy switches."""
from __future__ import annotations

from typing import Any, cast

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription, DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, HassJob
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity, event
from homeassistant.util import utcnow
from datetime import timedelta

from .coordinator import HKVCoordinator
from .const import DOMAIN
from .base import HKVWriteBaseEntityDescription

from collections.abc import Callable
from homeassistant.helpers.typing import StateType

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up HKV switch devices."""
    _LOGGER.debug("attempting to setup switch entities")
    coordinator: HKVCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    #_LOGGER.debug(coordinator.get_data()["devices"])
    descriptions = []
    #TODO cleanup
    devices = coordinator.get_data()["devices"]
    for dev_addr, dev_data in devices.items():
        # _LOGGER.error(f"{dev_addr=}")
        # _LOGGER.error(f"{dev_data=}")
        for name, val in dev_data.items():
            _LOGGER.debug(f"{name=}")
            _LOGGER.debug(f"{val=}")
            
            if name.startswith('Relais'):
                descriptions.append(HKVEntityDescription(
                    key=name,
                    name=name.replace('_', ' '),
                    slave=dev_addr,
                    keynum=int(name[6:]),
                ))

    entities = []
    entity = {}
    for description in descriptions:
        entity = description
        entities.append(
            HKVSwitch(
                hass,
                coordinator,
                entity
                ))
    _LOGGER.debug("adding switches")
    _LOGGER.debug(entities)
    async_add_entities(entities)


@dataclass
class HKVEntityDescription(SwitchEntityDescription, HKVWriteBaseEntityDescription):
    """Describes HKV switch entity."""

class HKVSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an HKV switch."""

    def __init__(self, hass: HomeAssistant, coordinator: HKVCoordinator, description: HKVEntityDescription) -> None:
        self.coordinator: HKVCoordinator = coordinator
        self.description: HKVEntityDescription = description
        self._attr_name = f"{description.name}"

        actual_id = description.slave

        self._attr_unique_id = f"{actual_id}_{self.description.key}"
        self.entity_id = f"{SWITCH_DOMAIN}.{DOMAIN}_{actual_id}_{self.description.key}"

        self._update_job = HassJob(self.async_schedule_update_ha_state)
        self._unsub_update = None
        super().__init__(coordinator)


    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the device."""
        #self.coordinator.set_value(dev_addr=self.description.slave, key=self.description.key, keynum=self.description.keynum, value=1)
        if self.description.key.startswith('Relais'):
            self.coordinator.hkv.set_relais((self.description.keynum,1),dst=self.description.slave)
        await self.coordinator.async_update_local_entry(dev_addr=self.description.slave, key=self.description.key, value=1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the device."""
        #self.coordinator.set_value(dev_addr=self.description.slave, key=self.description.key, keynum=self.description.keynum, value=0)
        if self.description.key.startswith('Relais'):
            self.coordinator.hkv.set_relais((self.description.keynum,0),dst=self.description.slave)
        await self.coordinator.async_update_local_entry(dev_addr=self.description.slave, key=self.description.key, value=0)

    @property
    def is_on(self) -> bool:
        data =  self.description.value_fn( self.coordinator.get_data(), self.description.slave, self.description.key)
        """Return true if switch is on."""
        return cast(bool, data)

    @property
    def available(self) -> bool:
        try:
            return self.description.key in self.coordinator.get_data()["devices"][self.description.slave]
        except Exception as e:
            _LOGGER.critical(e)
            _LOGGER.info(self.coordinator.get_data())
            return False

    @property
    def device_info(self) -> entity.DeviceInfo:
        """Return the device info."""
        return entity.DeviceInfo(
            identifiers={
                (DOMAIN, self.unique_id.split('_')[0])
            },
            name=self.unique_id.split('_')[0],
            model='HKV_Temp_Heltec' if self.unique_id.split('_')[0].startswith('59') else 'HKV_Temp_D1_mini', #self.unique_id.split('_')[0],
            manufacturer="holger", # to be dynamically set for gavazzi and redflow
        )
        
