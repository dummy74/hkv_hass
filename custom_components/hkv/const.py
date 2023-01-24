"""Constants for the HKV integration."""

from enum import Enum

DOMAIN = "hkv"

CONF_DEV = "dev"
CONF_BAUD = "baudrate"
SCAN_REGISTERS = "registers"
CONF_INTERVAL = "interval"


class EntityType():
    def __init__(self, entityTypeName) -> None:
        self.entityTypeName = entityTypeName

class ReadEntityType(EntityType):
    def __init__(self, entityTypeName: str = "read") -> None:
        super().__init__(entityTypeName=entityTypeName)

class TextReadEntityType(ReadEntityType):
    def __init__(self, decodeEnum: Enum) -> None:
        super().__init__()
        self.decodeEnum = decodeEnum

class BoolReadEntityType(ReadEntityType):
    def __init__(self) -> None:
        super().__init__(entityTypeName="bool")

class ButtonWriteType(EntityType):
    def __init__(self) -> None:
        super().__init__(entityTypeName="button")