"""Support for victron energy switches."""
from __future__ import annotations

from typing import Any, cast

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription, DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, HassJob
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity, event
from homeassistant.util import utcnow
from datetime import timedelta

from .coordinator import HKVCoordinator
from .const import DOMAIN
from .base import HKVBaseEntityDescription

from collections.abc import Callable
from homeassistant.helpers.typing import StateType

import logging
from homeassistant.helpers.entity import EntityCategory

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
            
            if name in ['DISPLAY','USB','LORA','RS485','RELAIS','SENSOR']:
                for no in ['USED','READY']:
                    descriptions.append(HKVEntityDescription(
                        key=name+'_'+no,
                        name=name.replace('_', ' ')+' '+no,
                        slave=dev_addr,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        value_fn=lambda data, slave, key: data['devices'][slave][key.split('_')[0]][key.split('_')[1]]
                    ))

    entities = []
    entity = {}
    for description in descriptions:
        entity = description
        entities.append(
            HKVBinarySensor(
                hass,
                coordinator,
                entity
                ))
    _LOGGER.debug("adding switches")
    _LOGGER.debug(entities)
    async_add_entities(entities)


@dataclass
class HKVEntityDescription(BinarySensorEntityDescription, HKVBaseEntityDescription):
    """Describes HKV switch entity."""
    

class HKVBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an HKV switch."""

    def __init__(self, hass: HomeAssistant, coordinator: HKVCoordinator, description: HKVEntityDescription) -> None:
        self.coordinator: HKVCoordinator = coordinator
        self.description: HKVEntityDescription = description
        self._attr_name = f"{description.name}"

        actual_id = description.slave

        self._attr_entity_category: self.description.entity_category
        self._attr_unique_id = f"{actual_id}_{self.description.key}"
        self.entity_id = f"{BINARY_SENSOR_DOMAIN}.{DOMAIN}_{actual_id}_{self.description.key}"

        self._update_job = HassJob(self.async_schedule_update_ha_state)
        self._unsub_update = None
        super().__init__(coordinator)
        
    @property
    def is_on(self) -> bool:
        data =  self.description.value_fn( self.coordinator.get_data(), self.description.slave, self.description.key)
        """Return true if switch is on."""
        return cast(bool, data)

    @property
    def available(self) -> bool:
        try:
            if any([self.description.key==k1+'_'+k2 for k1 in ['DISPLAY','USB','LORA','RS485','RELAIS','SENSOR'] for k2 in ['USED','READY']]):
                return True
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
        
