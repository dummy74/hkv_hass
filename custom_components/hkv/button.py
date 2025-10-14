"""Support for Victron energy button sensors."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, HassJob

from dataclasses import dataclass

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity

from homeassistant.components.button import ButtonEntityDescription, ButtonDeviceClass, ButtonEntity, DOMAIN as BUTTON_DOMAIN

from .coordinator import HKVCoordinator
from .base import HKVBaseEntityDescription
from .const import DOMAIN


import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Victron energy binary sensor entries."""
    _LOGGER.debug("attempting to setup button entities")
    coordinator: HKVCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    #_LOGGER.warning(coordinator.get_data()["devices"])
    descriptions = []
    #TODO cleanup
    
    descriptions.append(HKVEntityDescription(
        key="hello_all",
        name='Hello',
        slave=99,
        device_class=ButtonDeviceClass.IDENTIFY,
    ))
    
    
    devices = coordinator.get_data()["devices"]
    for dev_addr, dev_data in devices.items():
        # _LOGGER.error(f"{dev_addr=}")
        # _LOGGER.error(f"{dev_data=}")
        descriptions.append(HKVEntityDescription(
            key="reboot",
            name='Reboot',
            slave=dev_addr,
            device_class=ButtonDeviceClass.RESTART,
        ))
        descriptions.append(HKVEntityDescription(
            key="status_update",
            name='Status Update',
            slave=dev_addr,
            device_class=ButtonDeviceClass.RESTART,
        ))
        if True: #'Temp' in ''.join([str(k) for k in dev_data.keys()]):
            descriptions.append(HKVEntityDescription(
                key="calibrate_temps",
                name='Calibrate Temps',
                slave=dev_addr,
                device_class=ButtonDeviceClass.RESTART,
            ))
        for name, val in dev_data.items():
            _LOGGER.debug(f"{name=}")
            _LOGGER.debug(f"{val=}")
            

    entities = []
    for description in descriptions:
        entities.append(HKVButton(hass,coordinator,description))

    async_add_entities(entities, True)

class HKVEntityDescription(HKVBaseEntityDescription,ButtonEntityDescription):
    """Describes HKV button entity."""


class HKVButton(CoordinatorEntity, ButtonEntity):
    """A button implementation for HKV device."""

    def __init__(self, hass: HomeAssistant, coordinator: HKVCoordinator, description: HKVEntityDescription) -> None:
        self.coordinator: HKVCoordinator = coordinator
        self.description: HKVEntityDescription = description
        self._attr_name = f"{description.name}"

        actual_id = description.slave

        self._attr_unique_id = f"{actual_id}_{self.description.key}"
        self.entity_id = f"{BUTTON_DOMAIN}.{DOMAIN}_{actual_id}_{self.description.key}"

        self._update_job = HassJob(self.async_schedule_update_ha_state)
        self._unsub_update = None
        super().__init__(coordinator)

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.description.key == 'hello_all':
            await self.coordinator.hkv.hello(dst=-1)
        elif self.description.key == 'reboot':
            await self.coordinator.hkv.reboot(dst=self.description.slave)
        elif self.description.key == 'update_status':
            await self.coordinator.hkv.get_status(dst=self.description.slave)
        elif self.description.key == 'calibrate_temps':
            await self.coordinator.hkv.calibrate_temps(dst=self.description.slave)

    @property
    def available(self) -> bool:
        try:
            
            if self.description.key == 'reboot':
                return self.description.slave in self.coordinator.get_data()["devices"]
            elif self.description.key == 'update_status':
                return self.description.slave in self.coordinator.get_data()["devices"]
            elif self.description.key == 'calibrate_temps':
                return True #'Temp' in ''.join([str(k) for k in self.coordinator.get_data()["devices"][self.description.slave].keys()])
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
            model='HKV_Temp_Heltec' if self.unique_id.split('_')[0].startswith('59') else 'HKV_Coordinator' if self.unique_id.split('_')[0].startswith('99') else 'HKV_Temp_D1_mini', #self.unique_id.split('_')[0],
            manufacturer="holger", # to be dynamically set for gavazzi and redflow
        )
        
