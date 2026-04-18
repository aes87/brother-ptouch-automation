"""Protocol constants for the Brother Raster Command Reference.

Source: Brother "Software Developer's Manual — Raster Command Reference"
for PT-E550W / PT-P750W / PT-P710BT. Primary target: PT-P750W.
"""

from enum import IntEnum, IntFlag

# Print head geometry
PRINT_HEAD_PINS = 128
LINE_LENGTH_BYTES = PRINT_HEAD_PINS // 8  # 16
DPI = 180

# USB
USB_VENDOR_BROTHER = 0x04F9
USB_OUT_EP = 0x02
USB_IN_EP = 0x81
USB_TIMEOUT_MS = 15_000
USB_PACKET_SIZE = 0x40

# 25.4 mm @ 180 dpi — minimum tape length the printer will emit
MIN_TAPE_DOTS = 174

STATUS_PACKET_SIZE = 32


class PrinterProductId(IntEnum):
    PT_E550W = 0x2060
    PT_P750W = 0x2062
    PT_P710BT = 0x20AF


class Mode(IntFlag):
    AUTO_CUT = 0x40
    MIRROR_PRINTING = 0x80


class StatusOffset(IntEnum):
    ERROR_INFORMATION_1 = 8
    ERROR_INFORMATION_2 = 9
    MEDIA_WIDTH = 10
    MEDIA_TYPE = 11
    MODE = 15
    MEDIA_LENGTH = 17
    STATUS_TYPE = 18
    PHASE_TYPE = 19
    PHASE_NUMBER = 20
    NOTIFICATION_NUMBER = 22
    TAPE_COLOR = 24
    TEXT_COLOR = 25
    HARDWARE_SETTINGS = 26


class MediaType(IntEnum):
    NO_MEDIA = 0x00
    LAMINATED_TAPE = 0x01
    NON_LAMINATED_TAPE = 0x03
    HEAT_SHRINK_TUBE = 0x11
    INCOMPATIBLE = 0xFF


class StatusType(IntEnum):
    REPLY_TO_REQUEST = 0x00
    PRINTING_COMPLETED = 0x01
    ERROR_OCCURRED = 0x02
    TURNED_OFF = 0x04
    NOTIFICATION = 0x05
    PHASE_CHANGE = 0x06


class ErrorInformation1(IntFlag):
    NO_MEDIA = 0x01
    CUTTER_JAM = 0x04
    WEAK_BATTERIES = 0x08
    HIGH_VOLTAGE_ADAPTER = 0x40


class ErrorInformation2(IntFlag):
    WRONG_MEDIA = 0x01
    COVER_OPEN = 0x10
    OVERHEATING = 0x20


# Raster command opcodes
CMD_ESC = 0x1B
CMD_INITIALIZE = b"\x1B\x40"  # ESC @
CMD_DYNAMIC_MODE_RASTER = b"\x1B\x69\x61\x01"
CMD_ENABLE_STATUS_NOTIFICATION = b"\x1B\x69\x21\x00"
CMD_PRINT_INFORMATION_PREFIX = b"\x1B\x69\x7A"
CMD_MODE_PREFIX = b"\x1B\x69\x4D"
CMD_ADVANCED_MODE_PREFIX = b"\x1B\x69\x4B"
CMD_MARGIN_PREFIX = b"\x1B\x69\x64"
CMD_COMPRESSION_TIFF = b"\x4D\x02"
CMD_RASTER_LINE = b"\x47"
CMD_RASTER_ZERO_LINE = b"\x5A"
CMD_PRINT_AND_FEED = b"\x1A"
CMD_STATUS_REQUEST = b"\x1B\x69\x53"
INVALIDATE_BYTES = b"\x00" * 100

# Default feed margin (dots @ 180 DPI). 14 dots ≈ 2 mm, matches the physical cut margin.
DEFAULT_FEED_DOTS = 14
