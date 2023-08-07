from enum import Enum

class Magic:
    MAGIC = 0x58881688
    EXT_MAGIC = 0x58891689

class AddressingMode(Enum):
    NORMAL = -1
    BACKWARD = 0

class Pattern:
    LOADADDR = bytes.fromhex('10ff2fe1')