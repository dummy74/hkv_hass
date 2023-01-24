from collections.abc import Callable
from homeassistant.helpers.typing import StateType

from dataclasses import dataclass
from homeassistant.helpers.entity import EntityDescription

@dataclass
class HKVBaseEntityDescription(EntityDescription):
    slave: int = None 
    value_fn: Callable[[dict], StateType] = lambda data, slave, key: data['devices'][slave][key]
@dataclass 
class HKVWriteBaseEntityDescription(HKVBaseEntityDescription):
    keynum: int = None