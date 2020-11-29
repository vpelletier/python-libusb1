import collections
import threading

from types import TracebackType
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Optional, Tuple, Type, Union

from . import libusb1

Version = collections.namedtuple('Version', ['major', 'minor', 'micro', 'nano', 'rc', 'describe'])

EVENT_CALLBACK_SET: FrozenSet[int]

class USBError(Exception):
    value: int

USBErrorAccess: USBError
USBErrorBusy: USBError
USBErrorIO: USBError
USBErrorInterrupted: USBError
USBErrorInvalidParam: USBError
USBErrorNoDevice: USBError
USBErrorNoMem: USBError
USBErrorNotFound: USBError
USBErrorNotSupported: USBError
USBErrorOther: USBError
USBErrorOverflow: USBError
USBErrorPipe: USBError
USBErrorTimeout: USBError

class DoomedTransferError(Exception): ...

# Type Aliases
Buffer = Union[bytes, bytearray]
BufferList = List[Buffer]
BufferOrLength = Union[Buffer, int]
Endpoint = int
UserData = object
Timeout = int
PollTimeout = Union[float, int, None]
TransferType = int
TransferStatus = int
TransferCallback = Callable[['USBTransfer'], None]
ErrorCallback = Callable[[int], None]
FileDescriptor = int
Events = Any
FDNotifierCallback = Callable[[int, int, Any], None]
RegisterCallback = Callable[['USBContext', 'USBDevice', int], None]

class USBTransfer:
    def __init__(self,
                 handle: libusb1.libusb_device_handle_p_alias,
                 iso_packets: int,
                 before_submit: TransferCallback,
                 after_completion: TransferCallback) -> None: ...
    def close(self) -> None: ...
    def doom(self) -> None: ...
    def __del__(self) -> None: ...
    def setCallback(self, callback: TransferCallback) -> None: ...
    def getCallback(self) -> TransferCallback: ...
    def setControl(self,
                   request_type: int,
                   request: int,
                   value: int,
                   index: int,
                   buffer_or_len: BufferOrLength,
                   callback: Optional[TransferCallback] = ...,
                   user_data: Optional[UserData] = ...,
                   timeout: Timeout = ...) -> None: ...
    def setBulk(self,
                endpoint: Endpoint,
                buffer_or_len: BufferOrLength,
                callback: Optional[TransferCallback] = ...,
                user_data: Optional[UserData] = ...,
                timeout: Timeout = ...) -> None: ...
    def setInterrupt(self,
                     endpoint: Endpoint,
                     buffer_or_len: BufferOrLength,
                     callback: Optional[TransferCallback] = ...,
                     user_data: Optional[UserData] = ...,
                     timeout: Timeout = ...) -> None: ...
    def setIsochronous(self,
                       endpoint: Endpoint,
                       buffer_or_len: BufferOrLength,
                       callback: Optional[TransferCallback] = ...,
                       user_data: Optional[UserData] = ...,
                       timeout: Timeout = ...,
                       iso_transfer_length_list: Optional[List[int]] = ...) -> None: ...
    def getType(self) -> TransferType: ...
    def getEndpoint(self) -> Endpoint: ...
    def getStatus(self) -> TransferStatus: ...
    def getActualLength(self) -> int: ...
    def getBuffer(self) -> Buffer: ...
    def getUserData(self) -> UserData: ...
    def setUserData(self, user_data: UserData) -> None: ...
    def getISOBufferList(self) -> BufferList: ...
    def getISOSetupList(self) -> List[Dict[str, int]]: ...
    def iterISO(self) -> None: ...
    def setBuffer(self,
                  buffer_or_len: BufferOrLength) -> None: ...
    def isSubmitted(self) -> bool: ...
    def submit(self) -> None: ...
    def cancel(self) -> None: ...

class USBTransferHelper:
    def __init__(self,
                 transfer: Optional[USBTransfer] = ...) -> None: ...
    def submit(self) -> None: ...
    def cancel(self) -> None: ...
    def setEventCallback(self,
                         event: int,
                         callback: TransferCallback) -> None: ...
    def setDefaultCallback(self,
                           callback: TransferCallback) -> None: ...
    def getEventCallback(self,
                         event: int,
                         default: Optional[TransferCallback] = ...) -> Optional[TransferCallback]: ...
    def __call__(self,
                 transfer: USBTransfer) -> None: ...
    def isSubmited(self) -> bool: ...

class USBPollerThread(threading.Thread):
    daemon: bool = ...

    def __init__(self,
                 context: USBContext,
                 poller: USBPoller,
                 exc_callback: Optional[ErrorCallback] = ...) -> None: ...
    def stop(self) -> None: ...
    @staticmethod
    def exceptionHandler(exc: BaseException) -> None: ...
    def run(self) -> None: ...

class USBPoller:
    def __init__(self,
                 context: USBContext,
                 poller: USBPoller) -> None: ...
    def __del__(self) -> None: ...
    def poll(self,
             timeout: PollTimeout = ...) -> List[Tuple[int, int]]: ...
    def register(self,
                 fd: FileDescriptor, events: Events) -> None: ...
    def unregister(self,
                   fd: FileDescriptor) -> None: ...

class _ReleaseInterface:
    def __init__(self,
                 handle: USBDeviceHandle,
                 interface: int) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None: ...

class USBDeviceHandle:
    def __init__(self,
                 context: USBContext,
                 handle: libusb1.libusb_device_handle_p_alias,
                 device: USBDevice) -> None: ...
    def __del__(self) -> None: ...
    def close(self) -> None: ...
    def getDevice(self) -> USBDevice: ...
    def getConfiguration(self) -> int: ...
    def setConfiguration(self,
                         configuration: int) -> None: ...
    def getManufacturer(self) -> str: ...
    def getProduct(self) -> str: ...
    def getSerialNumber(self) -> str: ...
    def claimInterface(self,
                       interface: int) -> _ReleaseInterface: ...
    def releaseInterface(self,
                         interface: int) -> None: ...
    def setInterfaceAltSetting(self,
                               interface: int,
                               alt_setting: int) -> None: ...
    def clearHalt(self,
                  endpoint: int) -> None: ...
    def resetDevice(self) -> None: ...
    def kernelDriverActive(self,
                           interface: int) -> bool: ...
    def detachKernelDriver(self,
                           interface: int) -> None: ...
    def attachKernelDriver(self,
                           interface: int) -> None: ...
    def setAutoDetachKernelDriver(self,
                                  enable: bool) -> None: ...
    def getSupportedLanguageList(self) -> List[int]: ...
    def getStringDescriptor(self,
                            descriptor: int,
                            lang_id: int,
                            errors: str = ...) -> str: ...
    def getASCIIStringDescriptor(self,
                                 descriptor: int,
                                 errors: str = ...) -> str: ...
    def controlWrite(self,
                     request_type: int,
                     request: int,
                     value: int,
                     index: int,
                     data: bytes,
                     timeout: int = ...) -> int: ...
    def controlRead(self,
                    request_type: int,
                    request: int,
                    value: int,
                    index: int,
                    length: int,
                    timeout: int = ...) -> bytes: ...
    def bulkWrite(self,
                  endpoint: int,
                  data: bytes,
                  timeout: int = ...) -> int: ...
    def bulkRead(self,
                 endpoint: int,
                 length: int,
                 timeout: int = ...) -> bytes: ...
    def interruptWrite(self,
                       endpoint: int,
                       data: bytes,
                       timeout: int = ...) -> int: ...
    def interruptRead(self,
                      endpoint: int,
                      length: int,
                      timeout: int = ...) -> bytes: ...
    def getTransfer(self,
                    iso_packets: int = ...) -> USBTransfer: ...

class USBConfiguration:
    def __init__(self,
                 context: USBContext,
                 config: libusb1.libusb_config_descriptor,
                 device_speed: int) -> None: ...
    def __iter__(self) -> Iterator[USBInterface]: ...
    def __getitem__(self,
                    interface: int) -> USBInterface: ...
    def getNumInterfaces(self) -> int: ...
    def getConfigurationValue(self) -> int: ...
    def getDescriptor(self) -> int: ...
    def getAttributes(self) -> int: ...
    def getMaxPower(self) -> int: ...
    def getExtra(self) -> List[bytearray]: ...
    def iterInterfaces(self) -> Iterator[USBInterface]: ...

class USBInterface:
    def __init__(self,
                 context: USBContext,
                 interface: int) -> None: ...
    def __len__(self)-> int: ...
    def __iter__(self) -> Iterator[USBInterfaceSetting]: ...
    def __getitem__(self,
                    alt_setting: int) -> USBInterfaceSetting: ...
    def getNumSettings(self) -> int: ...
    def iterSettings(self) -> Iterator[USBInterfaceSetting]: ...

class USBInterfaceSetting:
    def __init__(self,
                 context: USBContext,
                 alt_setting: libusb1.libusb_interface_descriptor_p_alias) -> None: ...
    def __iter__(self) -> Iterator[USBEndpoint]: ...
    def __len__(self) -> int: ...
    def __getitem__(self,
                    endpoint: int) -> USBEndpoint: ...
    def getNumber(self) -> int: ...
    def getAlternateSetting(self) -> int: ...
    def getNumEndpoints(self) -> int: ...
    def getClass(self) -> int: ...
    def getSubClass(self) -> int: ...
    def getClassTuple(self) -> Tuple[int, int]: ...
    def getClassTupple(self) -> Tuple[int, int]: ...
    def getProtocol(self) -> int: ...
    def getDescriptor(self) -> int: ...
    def getExtra(self) -> List[bytearray]: ...
    def iterEndpoints(self) -> Iterator[USBEndpoint]: ...

class USBEndpoint:
    def __init__(self,
                 context: USBContext,
                 endpoint: libusb1.libusb_endpoint_descriptor_p_alias) -> None: ...
    def getAddress(self) -> int: ...
    def getAttributes(self) -> int: ...
    def getMaxPacketSize(self) -> int: ...
    def getInterval(self) -> int: ...
    def getRefresh(self) -> int: ...
    def getSyncAddress(self) -> int: ...
    def getExtra(self) -> List[bytearray]: ...

class USBDevice:
    device_p: libusb1.libusb_device_p_alias = ...
    device_descriptor: Any = ...

    def __init__(self,
                 context: USBContext,
                 device_p: libusb1.libusb_device_p_alias,
                 can_load_configuration: bool = ...) -> None: ...
    def __del__(self) -> None: ...
    def __len__(self) -> int: ...
    def __getitem__(self,
                    index: int) -> USBConfiguration: ...
    def __hash__(self) -> int: ...
    def __eq__(self,
               other: Any) -> bool: ...
    def close(self) -> None: ...
    def iterConfigurations(self) -> Iterator[USBConfiguration]: ...
    def iterConfiguations(self) -> Iterator[USBConfiguration]: ...
    def iterSettings(self) -> Iterator[USBInterfaceSetting]: ...
    def getBusNumber(self) -> int: ...
    def getPortNumber(self) -> int: ...
    def getPortNumberList(self) -> List[int]: ...
    def getDeviceAddress(self) -> int: ...
    def getbcdUSB(self) -> int: ...
    def getDeviceClass(self) -> int: ...
    def getDeviceSubClass(self) -> int: ...
    def getDeviceProtocol(self) -> int: ...
    def getMaxPacketSize0(self) -> int: ...
    def getMaxPacketSize(self,
                         endpoint: int) -> int: ...
    def getMaxISOPacketSize(self,
                            endpoint: int) -> int: ...
    def getVendorID(self) -> int: ...
    def getProductID(self) -> int: ...
    def getbcdDevice(self) -> int: ...
    def getSupportedLanguageList(self) -> List[int]: ...
    def getManufacturer(self) -> int: ...
    def getManufacturerDescriptor(self) -> str: ...
    def getProduct(self) -> str: ...
    def getProductDescriptor(self) -> int: ...
    def getSerialNumber(self) -> str: ...
    def getSerialNumberDescriptor(self) -> int: ...
    def getNumConfigurations(self) -> int: ...
    def getDeviceSpeed(self) -> int: ...
    def open(self) -> USBDeviceHandle: ...

class USBContext:
    def __init__(self) -> None: ...
    def __del__(self) -> None: ...
    def __enter__(self) -> USBContext: ...
    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None: ...
    def open(self) -> USBContext: ...
    def close(self) -> None: ...
    def exit(self) -> None: ...
    def getDeviceIterator(self,
                          skip_on_error: bool = ...) -> Iterator[USBDevice]: ...
    def getDeviceList(self,
                      skip_on_access_error: bool = ...,
                      skip_on_error: bool = ...) -> List[USBDevice]: ...
    def getByVendorIDAndProductID(self,
                                  vendor_id: Any,
                                  product_id: Any,
                                  skip_on_access_error: bool = ...,
                                  skip_on_error: bool = ...) -> Optional[USBDevice]: ...
    def openByVendorIDAndProductID(self,
                                   vendor_id: Any,
                                   product_id: Any,
                                   skip_on_access_error: bool = ...,
                                   skip_on_error: bool = ...) -> Optional[USBDeviceHandle]: ...
    def getPollFDList(self) -> Tuple[int, int]: ...
    def handleEvents(self) -> None: ...
    def handleEventsTimeout(self,
                            tv: int = ...) -> None: ...
    def setPollFDNotifiers(self,
                           added_cb: Optional[FDNotifierCallback] = ...,
                           removed_cb: Optional[FDNotifierCallback] = ...,
                           user_data: Optional[UserData] = ...) -> None: ...
    def getNextTimeout(self) -> int: ...
    def setDebug(self,
                 level: int) -> None: ...
    def tryLockEvents(self) -> int: ...
    def lockEvents(self) -> None: ...
    def lockEventWaiters(self) -> None: ...
    def waitForEvent(self,
                     tv: int = ...) -> None: ...
    def unlockEventWaiters(self) -> None: ...
    def eventHandlingOK(self) -> int: ...
    def unlockEvents(self) -> None: ...
    def handleEventsLocked(self) -> None: ...
    def eventHandlerActive(self) -> int: ...
    @staticmethod
    def hasCapability(capability: int) -> int: ...
    def hotplugRegisterCallback(self,
                                callback: RegisterCallback,
                                events: int = ...,
                                flags: int = ...,
                                vendor_id: int = ...,
                                product_id: int = ...,
                                dev_class: int = ...) -> int: ...
    def hotplugDeregisterCallback(self,
                                  handle: int) -> None: ...

def getVersion() -> Version: ...
def hasCapability(capability: int) -> int: ...

class LibUSBContext(USBContext):
    def __init__(self) -> None: ...

# Enums
CLASS_PER_INTERFACE: int
CLASS_AUDIO: int
CLASS_COMM: int
CLASS_HID: int
CLASS_PHYSICAL: int
CLASS_PTP: int
CLASS_IMAGE = libusb1
CLASS_PRINTER: int
CLASS_MASS_STORAGE: int
CLASS_HUB: int
CLASS_DATA: int
CLASS_SMART_CARD: int
CLASS_CONTENT_SECURITY: int
CLASS_VIDEO: int
CLASS_PERSONAL_HEALTHCARE: int
CLASS_DIAGNOSTIC_DEVICE: int
CLASS_WIRELESS: int
CLASS_APPLICATION: int
CLASS_VENDOR_SPEC: int

DT_DEVICE: int
DT_CONFIG: int
DT_STRING: int
DT_INTERFACE: int
DT_ENDPOINT: int
DT_HID: int
DT_REPORT: int
DT_PHYSICAL: int
DT_HUB: int

DT_DEVICE_SIZE: int
DT_CONFIG_SIZE: int
DT_INTERFACE_SIZE: int
DT_ENDPOINT_SIZE: int
DT_ENDPOINT_AUDIO_SIZE: int
DT_HUB_NONVAR_SIZE: int

ENDPOINT_ADDRESS_MASK: int
USB_ENDPOINT_ADDRESS_MASK: int
ENDPOINT_DIR_MASK: int
USB_ENDPOINT_DIR_MASK: int

ENDPOINT_IN: int
ENDPOINT_OUT: int

TRANSFER_TYPE_MASK: int

TRANSFER_TYPE_CONTROL: int
TRANSFER_TYPE_ISOCHRONOUS: int
TRANSFER_TYPE_BULK: int
TRANSFER_TYPE_INTERRUPT: int

REQUEST_GET_STATUS: int
REQUEST_CLEAR_FEATURE: int
REQUEST_SET_FEATURE: int
REQUEST_SET_ADDRESS: int
REQUEST_GET_DESCRIPTOR: int
REQUEST_SET_DESCRIPTOR: int
REQUEST_GET_CONFIGURATION: int
REQUEST_SET_CONFIGURATION: int
REQUEST_GET_INTERFACE: int
REQUEST_SET_INTERFACE: int
REQUEST_SYNCH_FRAME: int

REQUEST_TYPE_STANDARD: int
REQUEST_TYPE_CLASS: int
REQUEST_TYPE_VENDOR: int
REQUEST_TYPE_RESERVED: int
TYPE_STANDARD: int
TYPE_CLASS: int
TYPE_VENDOR: int
TYPE_RESERVED: int

RECIPIENT_DEVICE: int
RECIPIENT_INTERFACE: int
RECIPIENT_ENDPOINT: int
RECIPIENT_OTHER: int

ISO_SYNC_TYPE_MASK: int

ISO_SYNC_TYPE_NONE: int
ISO_SYNC_TYPE_ASYNC: int
ISO_SYNC_TYPE_ADAPTIVE: int
ISO_SYNC_TYPE_SYNC: int

ISO_USAGE_TYPE_MASK: int

ISO_USAGE_TYPE_DATA: int
ISO_USAGE_TYPE_FEEDBACK: int
ISO_USAGE_TYPE_IMPLICIT: int

CONTROL_SETUP_SIZE: int

SPEED_UNKNOWN: int
SPEED_LOW: int
SPEED_FULL: int
SPEED_HIGH: int
SPEED_SUPER: int

LOW_SPEED_OPERATION: int
FULL_SPEED_OPERATION: int
HIGH_SPEED_OPERATION: int
SUPER_SPEED_OPERATION: int

SUCCESS: int
ERROR_IO: int
ERROR_INVALID_PARAM: int
ERROR_ACCESS: int
ERROR_NO_DEVICE: int
ERROR_NOT_FOUND: int
ERROR_BUSY: int
ERROR_TIMEOUT: int
ERROR_OVERFLOW: int
ERROR_PIPE: int
ERROR_INTERRUPTED: int
ERROR_NO_MEM: int
ERROR_NOT_SUPPORTED: int
ERROR_OTHER: int

TRANSFER_COMPLETED: int
TRANSFER_ERROR: int
TRANSFER_TIMED_OUT: int
TRANSFER_CANCELLED: int
TRANSFER_STALL: int
TRANSFER_NO_DEVICE: int
TRANSFER_OVERFLOW: int

TRANSFER_SHORT_NOT_OK: int
TRANSFER_FREE_BUFFER: int
TRANSFER_FREE_TRANSFER: int
TRANSFER_ADD_ZERO_PACKET: int

CAP_HAS_CAPABILITY: int
CAP_HAS_HOTPLUG: int
CAP_HAS_HID_ACCESS: int
CAP_SUPPORTS_DETACH_KERNEL_DRIVER: int

LOG_LEVEL_NONE: int
LOG_LEVEL_ERROR: int
LOG_LEVEL_WARNING: int
LOG_LEVEL_INFO: int
LOG_LEVEL_DEBUG: int

HOTPLUG_EVENT_DEVICE_ARRIVED: int
HOTPLUG_EVENT_DEVICE_LEFT: int

HOTPLUG_MATCH_ANY: int
