"""Support for Victron energy sensors."""

from dataclasses import dataclass

import logging

from datetime import timedelta
from homeassistant.util import utcnow
from homeassistant.helpers import event, entity
from homeassistant.core import HomeAssistant, HassJob
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorEntity, DOMAIN as SENSOR_DOMAIN,\
    SensorStateClass

from .coordinator import HKVCoordinator
from .base import HKVBaseEntityDescription
from .const import DOMAIN, ReadEntityType, TextReadEntityType, BoolReadEntityType

from homeassistant.const import (
    PERCENTAGE, 
    UnitOfEnergy, 
    UnitOfPower,
    ELECTRIC_POTENTIAL_VOLT,
    ELECTRIC_CURRENT_AMPERE,
    FREQUENCY_HERTZ,
    TIME_SECONDS,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfSpeed,
    UnitOfPressure
)

from collections.abc import Callable
from homeassistant.helpers.typing import StateType

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,) -> None:
    """Set up HKV energy sensor entries."""
    _LOGGER.debug("attempting to setup sensor entities")
    coordinator: HKVCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    #_LOGGER.warning(coordinator.get_data()["devices"])
    descriptions = []
    #TODO cleanup
    devices = coordinator.get_data()["devices"]
    for dev_addr, dev_data in devices.items():
        # _LOGGER.error(f"{dev_addr=}")
        # _LOGGER.error(f"{dev_data=}")
        for name, val in dev_data.items():
            _LOGGER.debug(f"{name=}")
            _LOGGER.debug(f"{val=}")
    
            # if name == 'SENSOR':
            #     value_fn = lambda data, slave, key: data['devices'][slave][key.split('_')[0]][key.split('_')[1]]
            #     for name2,val2 in val.items():
            #         if name2.startswith('ADDR'):
            #             value_fn = lambda data, slave, key: data['devices'][slave][key.split('_')[0]][key.split('_')[1]][2:]
            #         if name2.startswith('ADDR') or name=='NUM':  
            #             descriptions.append(HKVEntityDescription(
            #                 key=name+'_'+name2,
            #                 name=name+' '+name2,
            #                 native_unit_of_measurement=None,
            #                 state_class=SensorStateClass.TOTAL,
            #                 slave=dev_addr,
            #                 device_class=None,
            #                 entity_type=None,
            #                 value_fn = value_fn,
            #                 ))
            #
            # el
            if name in ['TDATA']:
                for i,t in enumerate(val):
                    descriptions.append(HKVEntityDescription(
                        key=f"{name}_{i}",
                        name=f"Temp {i+1}",
                        native_unit_of_measurement='°C',
                        state_class=SensorStateClass.MEASUREMENT,
                        slave=dev_addr,
                        device_class=SensorDeviceClass.TEMPERATURE,
                        entity_type=None,
                        value_fn=lambda data, slave, key: data['devices'][slave][key.split('_')[0]][int(key.split('_')[1])-1],
                ))
            elif name in ['MCNT','SNUM','RNUM','CCNT']:
                descriptions.append(HKVEntityDescription(
                    key=name,
                    name=name.replace('_', ' '),
                    native_unit_of_measurement='',
                    state_class=SensorStateClass.MEASUREMENT,
                    slave=dev_addr,
                    device_class=None,
                    entity_type=None,
                ))
                
                

    entities = []
    entity = {}
    for description in descriptions:
        entity = description
        entities.append(HKVSensor(coordinator,entity))

    # Add an entity for each sensor type
    async_add_entities(entities, True)

@dataclass
class HKVEntityDescription(SensorEntityDescription, HKVBaseEntityDescription):
    """Describes victron sensor entity."""
    entity_type: ReadEntityType = None
    
class HKVSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Victron energy sensor."""

    def __init__(self, coordinator: HKVCoordinator, description: HKVEntityDescription) -> None:
        """Initialize the sensor."""
        self.description: HKVEntityDescription = description
        self._attr_device_class = description.device_class
        self._attr_name = f"{description.name}"
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class
        self.entity_type = description.entity_type

        actual_id = description.slave

        self._attr_unique_id = f"{actual_id}_{self.description.key}"
        self.entity_id = f"{SENSOR_DOMAIN}.{DOMAIN}_{actual_id}_{self.description.key}"



        self._update_job = HassJob(self.async_schedule_update_ha_state)
        self._unsub_update = None

        super().__init__(coordinator)

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""      
        try:
            value = self.description.value_fn(self.coordinator.get_data(),self.description.slave,self.description.key)
            _LOGGER.debug(f"async_update: {self.description.slave=}, {self.description.key=}, {value=}")
            if self.entity_type is not None and isinstance(self.entity_type, TextReadEntityType):
                self._attr_native_value = self.entity_type.decodeEnum(value).name.split("_DUPLICATE")[0]
            else:
                self._attr_native_value = value
        except (TypeError, IndexError):
            _LOGGER.error("failed to retrieve value")
            # No data available
            self._attr_native_value = None

        # Cancel the currently scheduled event if there is any
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None
        
        # Schedule the next update at exactly the next whole hour sharp
        self._unsub_update = event.async_track_point_in_utc_time(
            self.hass,
            self._update_job,
            utcnow() + timedelta(seconds=self.coordinator.interval),
        )

    @property
    def available(self) -> bool:
        try:
            return bool(self.description.value_fn(self.coordinator.get_data(),self.description.slave,self.description.key))
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
        