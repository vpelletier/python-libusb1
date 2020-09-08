from ctypes import (Structure, c_int, c_uint8, pointer, c_uint32, c_char_p, c_ssize_t, c_uint16, c_uint, c_void_p,
                    py_object, LittleEndianStructure, CFUNCTYPE)
from typing import Any, Dict, List, Optional, Union

class Enum:
    forward_dict: Dict[str, int] = ...
    reverse_dict: Dict[int, str] = ...
    def __init__(self,
                 member_dict: Dict[str, int],
                 scope_dict: Dict[str, Any] = ...) -> None: ...
    def __call__(self,
                 value: int) -> str: ...
    def get(self,
            value: int,
            default: Optional[str] = ...) -> str: ...

def buffer_at(address: c_int,
              length: c_int) -> bytearray: ...
def newStruct(field_name_list: List[str]) -> LittleEndianStructure: ...
def newDescriptor(field_name_list: List[str]) -> LittleEndianStructure: ...

class USBError(Exception):
    value: Any = ...
    def __init__(self, value: Optional[Any] = ...) -> None: ...

def bswap16(x: int) -> int: ...
def libusb_cpu_to_le16(x: int) -> int: ...
def libusb_le16_to_cpu(x: int) -> int: ...

# Enums
libusb_class_code: Enum
LIBUSB_CLASS_PER_INTERFACE: int
LIBUSB_CLASS_AUDIO: int
LIBUSB_CLASS_COMM: int
LIBUSB_CLASS_HID: int
LIBUSB_CLASS_PHYSICAL: int
LIBUSB_CLASS_PTP: int
LIBUSB_CLASS_IMAGE: int
LIBUSB_CLASS_PRINTER: int
LIBUSB_CLASS_MASS_STORAGE: int
LIBUSB_CLASS_HUB: int
LIBUSB_CLASS_DATA: int
LIBUSB_CLASS_SMART_CARD: int
LIBUSB_CLASS_CONTENT_SECURITY: int
LIBUSB_CLASS_VIDEO: int
LIBUSB_CLASS_PERSONAL_HEALTHCARE: int
LIBUSB_CLASS_DIAGNOSTIC_DEVICE: int
LIBUSB_CLASS_WIRELESS: int
LIBUSB_CLASS_APPLICATION: int
LIBUSB_CLASS_VENDOR_SPEC: int

libusb_descriptor_type: Enum
LIBUSB_DT_DEVICE: int
LIBUSB_DT_CONFIG: int
LIBUSB_DT_STRING: int
LIBUSB_DT_INTERFACE: int
LIBUSB_DT_ENDPOINT: int
LIBUSB_DT_HID: int
LIBUSB_DT_REPORT: int
LIBUSB_DT_PHYSICAL: int
LIBUSB_DT_HUB: int

LIBUSB_DT_DEVICE_SIZE: int
LIBUSB_DT_CONFIG_SIZE: int
LIBUSB_DT_INTERFACE_SIZE: int
LIBUSB_DT_ENDPOINT_SIZE: int
LIBUSB_DT_ENDPOINT_AUDIO_SIZE: int
LIBUSB_DT_HUB_NONVAR_SIZE: int

LIBUSB_ENDPOINT_ADDRESS_MASK: int
USB_ENDPOINT_ADDRESS_MASK: int
LIBUSB_ENDPOINT_DIR_MASK: int
USB_ENDPOINT_DIR_MASK: int

libusb_endpoint_direction: Enum
LIBUSB_ENDPOINT_IN: int
LIBUSB_ENDPOINT_OUT: int

LIBUSB_TRANSFER_TYPE_MASK: int

libusb_transfer_type: Enum
LIBUSB_TRANSFER_TYPE_CONTROL: int
LIBUSB_TRANSFER_TYPE_ISOCHRONOUS: int
LIBUSB_TRANSFER_TYPE_BULK: int
LIBUSB_TRANSFER_TYPE_INTERRUPT: int

libusb_standard_request: Enum
LIBUSB_REQUEST_GET_STATUS: int
LIBUSB_REQUEST_CLEAR_FEATURE: int
LIBUSB_REQUEST_SET_FEATURE: int
LIBUSB_REQUEST_SET_ADDRESS: int
LIBUSB_REQUEST_GET_DESCRIPTOR: int
LIBUSB_REQUEST_SET_DESCRIPTOR: int
LIBUSB_REQUEST_GET_CONFIGURATION: int
LIBUSB_REQUEST_SET_CONFIGURATION: int
LIBUSB_REQUEST_GET_INTERFACE: int
LIBUSB_REQUEST_SET_INTERFACE: int
LIBUSB_REQUEST_SYNCH_FRAME: int

libusb_request_type: Enum
LIBUSB_REQUEST_TYPE_STANDARD: int
LIBUSB_TYPE_STANDARD: int
LIBUSB_REQUEST_TYPE_CLASS: int
LIBUSB_TYPE_CLASS: int
LIBUSB_REQUEST_TYPE_VENDOR: int
LIBUSB_TYPE_VENDOR: int
LIBUSB_REQUEST_TYPE_RESERVED: int
LIBUSB_TYPE_RESERVED: int

libusb_request_recipient: Enum
LIBUSB_RECIPIENT_DEVICE: int
LIBUSB_RECIPIENT_INTERFACE: int
LIBUSB_RECIPIENT_ENDPOINT: int
LIBUSB_RECIPIENT_OTHER: int

LIBUSB_ISO_SYNC_TYPE_MASK: int

libusb_iso_sync_type: Enum
LIBUSB_ISO_SYNC_TYPE_NONE: int
LIBUSB_ISO_SYNC_TYPE_ASYNC: int
LIBUSB_ISO_SYNC_TYPE_ADAPTIVE: int
LIBUSB_ISO_SYNC_TYPE_SYNC: int

LIBUSB_ISO_USAGE_TYPE_MASK: int

libusb_iso_usage_type: Enum
LIBUSB_ISO_USAGE_TYPE_DATA: int
LIBUSB_ISO_USAGE_TYPE_FEEDBACK: int
LIBUSB_ISO_USAGE_TYPE_IMPLICIT: int

LIBUSB_CONTROL_SETUP_SIZE: int

libusb_speed: Enum
LIBUSB_SPEED_UNKNOWN: int
LIBUSB_SPEED_LOW: int
LIBUSB_SPEED_FULL: int
LIBUSB_SPEED_HIGH: int
LIBUSB_SPEED_SUPER: int

libusb_supported_speed: Enum
LIBUSB_LOW_SPEED_OPERATION: int
LIBUSB_FULL_SPEED_OPERATION: int
LIBUSB_HIGH_SPEED_OPERATION: int
LIBUSB_5GBPS_OPERATION: int

libusb_error: Enum
LIBUSB_SUCCESS: int
LIBUSB_ERROR_IO: int
LIBUSB_ERROR_INVALID_PARAM: int
LIBUSB_ERROR_ACCESS: int
LIBUSB_ERROR_NO_DEVICE: int
LIBUSB_ERROR_NOT_FOUND: int
LIBUSB_ERROR_BUSY: int
LIBUSB_ERROR_TIMEOUT: int
LIBUSB_ERROR_OVERFLOW: int
LIBUSB_ERROR_PIPE: int
LIBUSB_ERROR_INTERRUPTED: int
LIBUSB_ERROR_NO_MEM: int
LIBUSB_ERROR_NOT_SUPPORTED: int
LIBUSB_ERROR_OTHER: int

libusb_transfer_status: Enum
LIBUSB_TRANSFER_COMPLETED: int
LIBUSB_TRANSFER_ERROR: int
LIBUSB_TRANSFER_TIMED_OUT: int
LIBUSB_TRANSFER_CANCELLED: int
LIBUSB_TRANSFER_STALL: int
LIBUSB_TRANSFER_NO_DEVICE: int
LIBUSB_TRANSFER_OVERFLOW: int

libusb_transfer_flags: Enum
LIBUSB_TRANSFER_SHORT_NOT_OK: int
LIBUSB_TRANSFER_FREE_BUFFER: int
LIBUSB_TRANSFER_FREE_TRANSFER: int
LIBUSB_TRANSFER_ADD_ZERO_PACKET: int

libusb_capability: Enum
LIBUSB_CAP_HAS_CAPABILITY: int
LIBUSB_CAP_HAS_HOTPLUG: int
LIBUSB_CAP_HAS_HID_ACCESS: int
LIBUSB_CAP_SUPPORTS_DETACH_KERNEL_DRIVER: int

libusb_log_level: Enum
LIBUSB_LOG_LEVEL_NONE: int
LIBUSB_LOG_LEVEL_ERROR: int
LIBUSB_LOG_LEVEL_WARNING: int
LIBUSB_LOG_LEVEL_INFO: int
LIBUSB_LOG_LEVEL_DEBUG: int

libusb_hotplug_flag: Enum
LIBUSB_HOTPLUG_ENUMERATE: int

libusb_hotplug_event: Enum
LIBUSB_HOTPLUG_EVENT_DEVICE_ARRIVED: int
LIBUSB_HOTPLUG_EVENT_DEVICE_LEFT: int

LIBUSB_HOTPLUG_MATCH_ANY: int

# Structures
class timeval(Structure): ...
class libusb_device_descriptor(Structure): ...
class libusb_endpoint_descriptor(Structure): ...
class libusb_interface_descriptor(Structure): ...
class libusb_interface(Structure): ...
class libusb_config_descriptor(Structure): ...
class libusb_control_setup(Structure): ...
class libusb_context(Structure): ...
class libusb_device(Structure): ...
class libusb_device_handle(Structure): ...
class libusb_version(Structure): ...
class libusb_iso_packet_descriptor(Structure): ...
class libusb_transfer(Structure): ...
class libusb_pollfd(Structure): ...

# Type Aliases
c_uchar = c_uint8
c_int_p_alias = pointer[c_int]

timeval_p_alias = pointer[timeval]
libusb_device_descriptor_p_alias = pointer[libusb_device_descriptor]
libusb_endpoint_descriptor_p_alias = pointer[libusb_endpoint_descriptor]
libusb_interface_descriptor_p_alias = pointer[libusb_interface_descriptor]
libusb_interface_p_alias = pointer[libusb_interface]
libusb_config_descriptor_p_alias = pointer[libusb_config_descriptor]
libusb_config_descriptor_p_p_alias = pointer[libusb_config_descriptor_p_alias]
libusb_control_setup_p_alias = pointer[libusb_control_setup]
libusb_context_p_alias = pointer[libusb_context]
libusb_context_p_p_alias = pointer[libusb_context_p_alias]
libusb_device_p_alias = pointer[libusb_device]
libusb_device_p_p_alias = pointer[libusb_device_p_alias]
libusb_device_p_p_p_alias = pointer[libusb_device_p_p_alias]
libusb_device_handle_p_alias = pointer[libusb_device_handle]
libusb_device_handle_p_p_alias = pointer[libusb_device_handle_p_alias]
libusb_version_p_alias = pointer[libusb_version]
libusb_iso_packet_descriptor_p_alias = pointer[libusb_iso_packet_descriptor]
libusb_transfer_p_alias = pointer[libusb_transfer]
libusb_transfer_cb_fn_p_alias = Any  # TODO
libusb_pollfd_p_alias = pointer[libusb_pollfd]
libusb_pollfd_p_p_alias = pointer[libusb_pollfd_p_alias]
libusb_pollfd_added_cb_p_alias = Any  # TODO
libusb_pollfd_removed_cb_p_alias = Any  # TODO
libusb_hotplug_callback_handle_alias = c_int
libusb_hotplug_callback_handle_p_alias = pointer[libusb_hotplug_callback_handle_alias]
libusb_hotplug_callback_fn_p_alias = Any   # TODO

libusb_descriptor_alias = Union[libusb_config_descriptor_p_alias,
                                libusb_endpoint_descriptor_p_alias,
                                libusb_interface_descriptor_p_alias]

# Type Variables
c_int_p: pointer[c_int]

timeval_p: pointer[timeval]
libusb_device_descriptor_p: libusb_device_descriptor_p_alias
libusb_endpoint_descriptor_p: libusb_endpoint_descriptor_p_alias
libusb_interface_descriptor_p:libusb_interface_descriptor_p_alias
libusb_interface_p: libusb_interface_p_alias
libusb_config_descriptor_p: libusb_interface_p_alias
libusb_config_descriptor_p_p: pointer[libusb_interface_p_alias]
libusb_control_setup_p: libusb_control_setup_p_alias
libusb_context_p: libusb_context_p_alias
libusb_context_p_p: libusb_context_p_p_alias
libusb_device_p: libusb_device_p_alias
libusb_device_p_p: libusb_device_p_p_alias
libusb_device_p_p_p: libusb_device_p_p_p_alias
libusb_device_handle_p: libusb_device_handle_p_alias
libusb_device_handle_p_p: libusb_device_handle_p_p_alias
libusb_iso_packet_descriptor_p: libusb_iso_packet_descriptor_p_alias
libusb_transfer_p: libusb_transfer_p_alias
libusb_transfer_cb_fn_p: libusb_transfer_cb_fn_p_alias
libusb_pollfd_p: libusb_pollfd_p_alias
libusb_pollfd_p_p: libusb_pollfd_p_p_alias
libusb_pollfd_added_cb_p: libusb_pollfd_added_cb_p_alias
libusb_pollfd_removed_cb_p: libusb_pollfd_removed_cb_p_alias
libusb_hotplug_callback_handle: libusb_hotplug_callback_handle_alias
libusb_hotplug_callback_fn_p: libusb_hotplug_callback_fn_p_alias


# Functions
def libusb_init(ctx: libusb_context_p_alias) -> None: ...
def libusb_exit(ctx: libusb_context_p_alias) -> None: ...
def libusb_set_debug(ctx: libusb_context_p_alias,
                     level: c_int) -> None: ...
def libusb_get_version() -> libusb_version_p_alias: ...
def libusb_has_capability(capability: c_uint32) -> c_int: ...
def libusb_error_name(errcode: c_int) -> c_char_p: ...
def libusb_strerror(errcode: c_int) -> None: ...
def libusb_get_device_list(ctx: libusb_context_p_alias,
                           list: libusb_device_p_p_p_alias) -> c_ssize_t: ...
def libusb_free_device_list(list: libusb_device_p_p_alias,
                            unref_devices: c_int) -> None: ...
def libusb_ref_device(dev: libusb_device_p_alias) -> libusb_device_p_alias: ...
def libusb_unref_device(dev: libusb_device_p_alias) -> None: ...
def libusb_get_configuration(dev: libusb_device_handle_p_alias,
                             config: pointer[c_int]) -> c_int: ...
def libusb_get_device_descriptor(dev: libusb_device_p_alias,
                                 desc: libusb_device_descriptor_p_alias) -> c_int: ...
def libusb_get_active_config_descriptor(dev: libusb_device_p_alias,
                                        config: libusb_config_descriptor_p_alias) -> c_int: ...
def libusb_get_config_descriptor(dev: libusb_device_p_alias,
                                 config_index: c_uint8,
                                 config: libusb_config_descriptor_p_p_alias) -> None: ...
def libusb_get_config_descriptor_by_value(dev: libusb_device_p_alias,
                                          bConfigurationValue: c_uint8,
                                          config: libusb_config_descriptor_p_p_alias) -> c_int: ...
def libusb_free_config_descriptor(config: libusb_config_descriptor_p_alias) -> None: ...
def libusb_get_bus_number(dev: libusb_device_p_alias) -> c_uint8: ...
def libusb_get_port_number(dev: libusb_device_p_alias) -> c_uint8: ...
def libusb_get_port_numbers(dev: libusb_device_p_alias,
                            port_numbers: pointer[c_uint8],
                            port_numbers_len: c_int) -> c_int: ...
def libusb_get_parent(dev: libusb_device_p_alias) -> libusb_device_p_alias: ...
def libusb_get_device_address(dev: libusb_device_p_alias) -> c_uint8: ...
def libusb_get_device_speed(dev: libusb_device_p_alias) -> c_int: ...
def libusb_get_max_packet_size(dev: libusb_device_p_alias,
                               endpoint: c_uint8) -> c_int: ...
def libusb_get_max_iso_packet_size(dev: libusb_device_p_alias,
                                   endpoint: c_uint8) -> c_int: ...
def libusb_open(dev: libusb_device_p_alias,
                handle: libusb_device_handle_p_p_alias) -> c_int: ...
def libusb_close(dev: libusb_device_p_alias) -> None: ...
def libusb_get_device(dev_handle: libusb_device_handle_p_alias) -> libusb_device_p_alias: ...
def libusb_set_configuration(dev: libusb_device_handle_p_alias,
                             configuration: c_int) -> c_int: ...
def libusb_claim_interface(dev: libusb_device_handle_p_alias,
                           iface: c_int) -> c_int: ...
def libusb_release_interface(dev: libusb_device_handle_p_alias,
                             iface: c_int) -> c_int: ...
def libusb_open_device_with_vid_pid(ctx: libusb_context_p_alias,
                                    vendor_id: c_uint16,
                                    product_id: c_uint16) -> libusb_device_handle_p_alias: ...
def libusb_set_interface_alt_setting(dev: libusb_device_handle_p_alias,
                                     interface_number: c_int,
                                     alternate_setting: c_int) -> c_int: ...
def libusb_clear_halt(dev: libusb_device_handle_p_alias,
                      endpoint: c_uchar) -> c_int: ...
def libusb_reset_device(dev: libusb_device_handle_p_alias) -> c_int: ...
def libusb_kernel_driver_active(dev: libusb_device_handle_p_alias,
                                interface: c_int) -> c_int: ...
def libusb_detach_kernel_driver(dev: libusb_device_handle_p_alias,
                                interface: c_int) -> c_int: ...
def libusb_attach_kernel_driver(dev: libusb_device_handle_p_alias,
                                interface: c_int) -> c_int: ...
def libusb_set_auto_detach_kernel_driver(dev: libusb_device_handle_p_alias,
                                         enable: c_int) -> c_int: ...
def libusb_control_transfer_get_data(transfer_p: libusb_transfer_p_alias) -> bytearray: ...
def libusb_control_transfer_get_setup(transfer_p: libusb_transfer_p_alias) -> libusb_control_setup_p_alias: ...
def libusb_fill_control_setup(setup_p: str,
                              bmRequestType: c_uint8,
                              bRequest: c_uint8,
                              wValue: c_uint16,
                              wIndex: c_uint16,
                              wLength: c_uint16) -> None: ...
def libusb_alloc_transfer(iso_packets: c_int) -> libusb_transfer_p_alias: ...
def libusb_submit_transfer(transfer: libusb_transfer_p_alias) -> c_int: ...
def libusb_cancel_transfer(transfer: libusb_transfer_p_alias) -> c_int: ...
def libusb_free_transfer(transfer: libusb_transfer_p_alias) -> None: ...
def libusb_fill_control_transfer(transfer_p: libusb_transfer_p_alias,
                                 dev_handle: libusb_device_handle_p_alias,
                                 buffer: c_void_p,
                                 callback: libusb_transfer_cb_fn_p_alias,
                                 user_data: c_void_p,
                                 timeout: c_uint) -> None: ...
def libusb_fill_bulk_transfer(transfer_p: libusb_transfer_p_alias,
                              dev_handle: libusb_device_handle_p_alias,
                              endpoint: c_uchar,
                              buffer: c_void_p,
                              length: c_int,
                              callback: libusb_transfer_cb_fn_p_alias,
                              user_data: c_void_p,
                              timeout: c_uint) -> None: ...
def libusb_fill_interrupt_transfer(transfer_p: libusb_transfer_p_alias,
                                   dev_handle: libusb_device_handle_p_alias,
                                   endpoint: c_uchar,
                                   buffer: c_void_p,
                                   length: c_int,
                                   callback: libusb_transfer_cb_fn_p_alias,
                                   user_data: c_void_p,
                                   timeout: c_uint) -> None: ...
def libusb_fill_iso_transfer(transfer_p: libusb_transfer_p_alias,
                             dev_handle: libusb_device_handle_p_alias,
                             endpoint: c_uchar,
                             buffer: c_void_p,
                             length: c_int,
                             num_iso_packets: c_int,
                             callback: libusb_transfer_cb_fn_p_alias,
                             user_data: c_void_p,
                             timeout: c_uint) -> None: ...
def get_iso_packet_list(transfer_p: libusb_transfer_p_alias) -> List[libusb_iso_packet_descriptor_p_alias]: ...
def get_iso_packet_buffer_list(transfer_p: libusb_transfer_p_alias) -> List[bytearray]: ...
def get_extra(descriptor: libusb_descriptor_alias) -> List[bytearray]: ...
def libusb_set_iso_packet_lengths(transfer_p: libusb_transfer_p_alias,
                                  length: c_int) -> None: ...
def libusb_get_iso_packet_buffer(transfer_p: libusb_transfer_p_alias,
                                 packet: c_int) -> bytearray: ...
def libusb_get_iso_packet_buffer_simple(transfer_p: libusb_transfer_p_alias,
                                        packet: c_int) -> bytearray: ...
def libusb_control_transfer(dev_handle: libusb_device_handle_p_alias,
                            request_type: c_uint8,
                            request: c_uint8,
                            value: c_uint16,
                            index: c_uint16,
                            data: c_void_p,
                            length: c_uint16,
                            timeout: c_uint) -> c_int: ...
def libusb_bulk_transfer(dev_handle: libusb_device_handle_p_alias,
                         endpoint: c_uchar,
                         data: c_void_p,
                         length: c_int,
                         actual_length: c_int,
                         timeout: c_uint) -> c_int: ...
def libusb_interrupt_transfer(dev_handle: libusb_device_handle_p_alias,
                              endpoint: c_uchar,
                              data: c_void_p,
                              length: c_int,
                              actual_length: c_int,
                              timeout: c_uint) -> c_int: ...
def libusb_get_descriptor(dev: libusb_device_handle_p_alias,
                          desc_type: c_uint16,
                          desc_index: c_uint16,
                          data: c_void_p,
                          length: c_uint16) -> c_int: ...
def libusb_get_string_descriptor(dev: libusb_device_handle_p_alias,
                                 desc_index: c_uint16,
                                 langid: c_uint16,
                                 data: c_void_p,
                                 length: c_uint16) -> c_int: ...
def libusb_get_string_descriptor_ascii(dev: libusb_device_handle_p_alias,
                                       index: c_uint8,
                                       data: c_void_p,
                                       length: c_int) -> c_int: ...
def libusb_try_lock_events(ctx: libusb_context_p_alias) -> c_int: ...
def libusb_lock_events(ctx: libusb_context_p_alias) -> c_int: ...
def libusb_unlock_events(ctx: libusb_context_p_alias) -> c_int: ...
def libusb_event_handling_ok(ctx: libusb_context_p_alias) -> c_int: ...
def libusb_event_handler_active(ctx: libusb_context_p_alias) -> c_int: ...
def libusb_lock_event_waiters(ctx: libusb_context_p_alias) -> None: ...
def libusb_unlock_event_waiters(ctx: libusb_context_p_alias) -> None: ...
def libusb_wait_for_event(ctx: libusb_context_p_alias,
                          tv: timeval_p_alias) -> c_int: ...
def libusb_handle_events_timeout(ctx: libusb_context_p_alias,
                                 tv: timeval_p_alias) -> c_int: ...
def libusb_handle_events_timeout_completed(ctx: libusb_context_p_alias,
                                           tv: timeval_p_alias,
                                           completed: c_int_p_alias) -> c_int: ...
def libusb_handle_events(ctx: libusb_context_p_alias) -> c_int: ...
def libusb_handle_events_completed(ctx: libusb_context_p_alias,
                                   completed: c_int_p_alias) -> c_int: ...
def libusb_handle_events_locked(ctx: libusb_context_p_alias,
                                tv: timeval_p_alias) -> c_int: ...
def libusb_get_next_timeout(ctx: libusb_context_p_alias,
                            tv: timeval_p_alias) -> c_int: ...
def libusb_get_pollfds(ctx: libusb_context_p_alias) -> libusb_pollfd_p_p_alias: ...
def libusb_set_pollfd_notifiers(ctx: libusb_context_p_alias,
                                added_cb: libusb_pollfd_added_cb_p_alias,
                                removed_cb: libusb_pollfd_removed_cb_p_alias,
                                user_data: c_void_p) -> None: ...
def libusb_hotplug_register_callback(ctx: libusb_context_p_alias,
                                     events: int,
                                     flag: int,
                                     vendor_id: int,
                                     product_id: int,
                                     dev_class: int,
                                     cb_fn: libusb_hotplug_callback_fn_p_alias,
                                     user_data: c_void_p,
                                     handle: libusb_hotplug_callback_handle_p_alias) -> c_int: ...
def libusb_hotplug_deregister_callback(ctx: libusb_context_p_alias,
                                       handle: libusb_hotplug_callback_handle_alias) -> None: ...
