"""Support for victron energy slider number entities."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional, cast

from homeassistant import config_entries
from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode, DOMAIN as NUMBER_DOMAIN


from homeassistant.const import TIME_SECONDS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import HKVCoordinator
from .base import HKVBaseEntityDescription
from .const import DOMAIN

from homeassistant.helpers.typing import StateType
from homeassistant.helpers import entity

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up victron switch devices."""
    _LOGGER.debug("attempting to setup button entities")
    coordinator: HKVCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    #_LOGGER.warning(coordinator.get_data()["devices"])
    descriptions = []
    #TODO cleanup
    devices = coordinator.get_data()["devices"]
    for dev_addr, dev_data in devices.items():
        # _LOGGER.error(f"{dev_addr=}")
        # _LOGGER.error(f"{dev_data=}")
        descriptions.append(HKVEntityDescription(
            key='temp_measure_interval',
            name='Temp. Mess-Interval',
            slave=dev_addr,
            native_unit_of_measurement='s',
            native_min_value=1000,
            native_max_value=3600000,
            native_step=1000,
            entity_category=EntityCategory.CONFIG,
        ))
        descriptions.append(HKVEntityDescription(
            key='temp_transmit_interval',
            name='Temp. Sende-Interval',
            slave=dev_addr,
            native_unit_of_measurement='s',
            native_min_value=1000,
            native_max_value=3600000,
            native_step=1000,
            entity_category=EntityCategory.CONFIG,
        ))

    entities = []
    entity = {}
    for description in descriptions:
        entity = description
        entities.append(
            HKVNumber(
                coordinator,
                entity
                ))
    _LOGGER.debug("adding number")
    async_add_entities(entities)
    _LOGGER.debug("adding numbering")

@dataclass
class HKVEntityDescription(NumberEntityDescription, HKVBaseEntityDescription):
    """Describes HKV number entity."""


class HKVNumber(NumberEntity):
    """HKV number."""

    description: HKVEntityDescription

    def __init__(self, coordinator: HKVCoordinator, description: HKVEntityDescription) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self.description = description
        self._attr_name = f"{description.name}"

        actual_id = description.slave

        self._attr_native_value = self.coordinator.get_data()['devices'][self.description.slave][self.description.key]

        self._attr_unique_id = f"{actual_id}_{self.description.key}"
        self.entity_id = f"{NUMBER_DOMAIN}.{DOMAIN}_{self.description.key}"

        self._attr_mode = NumberMode.BOX #SLIDER
  


    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self.description.key == 'temp_measure_interval':
            self.coordinator.hkv.set_temps_measure_period(delay=1000, period=int(value), dst=self.description.slave)
        elif self.description.key == 'temp_transmit_interval':
            self.coordinator.hkv.set_temps_transmit_period(delay=1000, period=int(value), dst=self.description.slave)
        await self.coordinator.async_update_local_entry(dev_addr=self.description.slave, key=self.description.key, value=value)


    @property
    def native_value(self) -> int:
        """Return the state of the entity."""
        data=self.coordinator.get_data()
        return data['devices'][self.description.slave][self.description.key]

    @property
    def native_step(self) -> float | None:
        return self.description.native_step

    @property
    def native_min_value(self) -> float:
        return self.description.native_min_value

    @property
    def native_max_value(self) -> float:
        return self.description.native_max_value

    @property
    def available(self) -> bool:
        try:
            if self.description.key == 'temp_measure_interval':
                return self.description.slave in self.coordinator.get_data()["devices"]
            elif self.description.key == 'temp_transmit_interval':
                return self.description.slave in self.coordinator.get_data()["devices"]
            return True
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