"""Support for Victron energy sensors."""

from dataclasses import dataclass
import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base import HKVBaseEntityDescription
from .const import DOMAIN, ReadEntityType, TextReadEntityType
from .coordinator import HKVCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,) -> None:
    """Set up HKV energy sensor entries."""
    _LOGGER.debug("attempting to setup sensor entities")
    coordinator: HKVCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    descriptions = []
    devices = coordinator.get_data()["devices"]
    for dev_addr, dev_data in devices.items():
        for name, val in dev_data.items():
            _LOGGER.debug(f"{name=}")
            _LOGGER.debug(f"{val=}")

            if name in ['TDATA']:
                for i, t in enumerate(val):
                    descriptions.append(HKVEntityDescription(
                        key=f"{name}_{i}",
                        name=f"Temp {i+1}",
                        native_unit_of_measurement='°C',
                        state_class=SensorStateClass.MEASUREMENT,
                        slave=dev_addr,
                        device_class=SensorDeviceClass.TEMPERATURE,
                        entity_type=None,
                        value_fn=lambda data, slave, key: data['devices'][slave][key.split('_')[0]][int(key.split('_')[1])],
                    ))
            elif name in ['MCNT', 'SNUM', 'RNUM', 'CCNT']:
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
    for description in descriptions:
        entities.append(HKVSensor(coordinator, description))

    async_add_entities(entities, True)

@dataclass
class HKVEntityDescription(SensorEntityDescription, HKVBaseEntityDescription):
    """Describes victron sensor entity."""
    entity_type: ReadEntityType = None

class HKVSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Victron energy sensor."""

    def __init__(self, coordinator: HKVCoordinator, description: HKVEntityDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.description: HKVEntityDescription = description
        self._attr_device_class = description.device_class
        self._attr_name = f"{description.name}"
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class
        self.entity_type = description.entity_type

        actual_id = description.slave

        self._attr_unique_id = f"{actual_id}_{self.description.key}"
        self.entity_id = f"{SENSOR_DOMAIN}.{DOMAIN}_{actual_id}_{self.description.key}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.description.value_fn(self.coordinator.get_data(), self.description.slave, self.description.key)
            _LOGGER.debug(f"update: {self.description.slave=}, {self.description.key=}, {value=}")
            if self.entity_type is not None and isinstance(self.entity_type, TextReadEntityType):
                self._attr_native_value = self.entity_type.decodeEnum(value).name.split("_DUPLICATE")[0]
            else:
                self._attr_native_value = value
        except (TypeError, IndexError):
            _LOGGER.error("failed to retrieve value")
            self._attr_native_value = None
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        try:
            return bool(self.description.value_fn(self.coordinator.get_data(), self.description.slave, self.description.key))
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
            model='HKV_Temp_Heltec' if self.unique_id.split('_')[0].startswith('59') else 'HKV_Coordinator' if self.unique_id.split('_')[0].startswith('99') else 'HKV_Temp_D1_mini',
            manufacturer="holger",
        )
