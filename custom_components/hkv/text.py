"""Support for victron energy switches."""
from __future__ import annotations

from typing import Any, cast

from dataclasses import dataclass

from homeassistant.components.text import TextEntity, TextEntityDescription, DOMAIN as TEXT_DOMAIN, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity
from homeassistant.helpers.entity import EntityCategory

from .coordinator import HKVCoordinator
from .const import DOMAIN
from .base import HKVBaseEntityDescription

from collections.abc import Callable
from homeassistant.helpers.typing import StateType

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up HKV text devices."""
    _LOGGER.debug("attempting to setup text entities")
    coordinator: HKVCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    descriptions = []
    devices = coordinator.get_data()["devices"]
    for dev_addr, dev_data in devices.items():
        for name, val in dev_data.items():
            _LOGGER.debug(f"{name=}")
            _LOGGER.debug(f"{val=}")
            
            if name == 'ID':
                descriptions.append(HKVEntityDescription(
                    key=name,
                    name=name.replace('_', ' '),
                    slave=dev_addr,
                    mode=TextMode.TEXT,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ))

    entities = []
    for description in descriptions:
        entities.append(HKVText(hass, coordinator, description))
    _LOGGER.debug("adding text entities")
    async_add_entities(entities)

@dataclass
class HKVEntityDescription(TextEntityDescription, HKVBaseEntityDescription):
    """Describes HKV text entity."""

class HKVText(CoordinatorEntity, TextEntity):
    """Representation of an HKV text."""

    def __init__(self, hass: HomeAssistant, coordinator: HKVCoordinator, description: HKVEntityDescription) -> None:
        super().__init__(coordinator)
        self.coordinator: HKVCoordinator = coordinator
        self.description: HKVEntityDescription = description
        self._attr_name = f"{description.name}"

        actual_id = description.slave

        self._attr_entity_category = self.description.entity_category
        self._attr_unique_id = f"{actual_id}_{self.description.key}"
        self.entity_id = f"{TEXT_DOMAIN}.{DOMAIN}_{actual_id}_{self.description.key}"

    @property
    def native_value(self) -> str:
        """Return the state of the entity."""
        data = self.coordinator.get_data()
        return str(data['devices'][self.description.slave].get(self.description.key, 'UNKNOWN'))

    @property
    def available(self) -> bool:
        try:
            return self.description.key in self.coordinator.get_data()["devices"][self.description.slave]
        except Exception as e:
            _LOGGER.critical(e)
            _LOGGER.info(self.coordinator.get_data())
            return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def device_info(self) -> entity.DeviceInfo:
        """Return the device info."""
        return entity.DeviceInfo(
            identifiers={
                (DOMAIN, self.unique_id.split('_')[0])
            },
            name=self.unique_id.split('_')[0],
            model='HKV_Temp_Heltec' if self.unique_id.split('_')[0].startswith('59') else 'HKV_Coordinator' if self.unique_id.split('_')[0].startswith('99') else 'HKV_Temp_D1_mini',
            manufacturer="holger",
        )