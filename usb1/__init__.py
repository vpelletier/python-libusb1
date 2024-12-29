# Copyright (C) 2010-2021  Vincent Pelletier <plr.vincent@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

# pylint: disable=invalid-name, too-many-locals, too-many-arguments
# pylint: disable=too-many-public-methods, too-many-instance-attributes
# pylint: disable=missing-docstring, too-many-lines
"""
Pythonic wrapper for libusb-1.0.

The first thing you must do is to get an "USB context". To do so, create an
USBContext instance.
Then, you can use it to browse available USB devices and open the one you want
to talk to.
At this point, you should have a USBDeviceHandle instance (as returned by
USBContext or USBDevice instances), and you can start exchanging with the
device.

Features:
- Basic device settings (configuration & interface selection, ...)
- String descriptor lookups (ASCII & unicode), and list supported language
  codes
- Synchronous I/O (control, bulk, interrupt)
- Asynchronous I/O (control, bulk, interrupt, isochronous)
  Note: Isochronous support is not well tested.
  See USBPoller, USBTransfer and USBTransferHelper.

All LIBUSB_* constants are available in this module, without the LIBUSB_
prefix - with one exception: LIBUSB_5GBPS_OPERATION is available as
SUPER_SPEED_OPERATION, so it is a valid python identifier.

All LIBUSB_ERROR_* constants are available in this module as exception classes,
subclassing USBError.
"""

import collections
import contextlib
from ctypes import byref, c_int, sizeof, POINTER, \
    cast, c_uint8, c_uint16, c_ubyte, c_void_p, cdll, addressof, \
    c_char
from ctypes.util import find_library
import functools
import inspect
import itertools
import sys
import threading
import warnings
import weakref
from . import _libusb1 as libusb1
from . import _version
__version__ = _version.get_versions()['version']
# pylint: disable=wrong-import-order,ungrouped-imports
if sys.platform == 'win32':
    from ctypes import get_last_error as get_errno
else:
    from ctypes import get_errno
# pylint: enable=wrong-import-order,ungrouped-imports

__all__ = [
    'USBContext', 'USBDeviceHandle', 'USBDevice', 'hasCapability',
    'USBPoller', 'USBTransfer', 'USBTransferHelper', 'EVENT_CALLBACK_SET',
    'USBEndpoint', 'USBInterfaceSetting', 'USBInterface',
    'USBConfiguration', 'DoomedTransferError', 'getVersion', 'USBError',
    'setLogCallback', 'setLocale',
    'loadLibrary',
]
# Bind libusb1 constants and libusb1.USBError to this module, so user does not
# have to import two modules.
USBError = libusb1.USBError
STATUS_TO_EXCEPTION_DICT = {}
def __bindConstants():
    global_dict = globals()
    PREFIX = 'LIBUSB_'
    for name, value in libusb1.__dict__.items():
        if name.startswith(PREFIX):
            name = name[len(PREFIX):]
            # Gah.
            if name == '5GBPS_OPERATION':
                name = 'SUPER_SPEED_OPERATION'
            assert name not in global_dict
            global_dict[name] = value
            __all__.append(name)
    # Finer-grained exceptions.
    for name, value in libusb1.libusb_error.forward_dict.items():
        if value:
            assert name.startswith(PREFIX + 'ERROR_'), name
            if name == 'LIBUSB_ERROR_IO':
                name = 'ErrorIO'
            else:
                name = ''.join(x.capitalize() for x in name.split('_')[1:])
            name = 'USB' + name
            assert name not in global_dict, name
            assert value not in STATUS_TO_EXCEPTION_DICT
            STATUS_TO_EXCEPTION_DICT[value] = global_dict[name] = type(
                name,
                (USBError, ),
                {'value': value},
            )
            __all__.append(name)
__bindConstants()
del __bindConstants

def raiseUSBError(
        value,
        # Avoid globals lookup on call to work during interpreter shutdown.
        __STATUS_TO_EXCEPTION_DICT=STATUS_TO_EXCEPTION_DICT,
        __USBError=USBError,
    ): # pylint: disable=dangerous-default-value
    raise __STATUS_TO_EXCEPTION_DICT.get(value, __USBError)(value)

def mayRaiseUSBError(
        value,
        # Avoid globals lookup on call to work during interpreter shutdown.
        __raiseUSBError=raiseUSBError,
    ):
    if value < 0:
        __raiseUSBError(value)
    return value

Version = collections.namedtuple(
    'Version',
    ['major', 'minor', 'micro', 'nano', 'rc', 'describe'],
)

# pylint: disable=undefined-variable
CONTROL_SETUP = b'\x00' * CONTROL_SETUP_SIZE
# pylint: enable=undefined-variable

# Default string length
# From a comment in libusb-1.0: "Some devices choke on size > 255"
STRING_LENGTH = 255

# As of v3 of USB specs, there cannot be more than 7 hubs from controller to
# device.
PATH_MAX_DEPTH = 7

EVENT_CALLBACK_SET = frozenset((
    # pylint: disable=undefined-variable
    TRANSFER_COMPLETED,
    TRANSFER_ERROR,
    TRANSFER_TIMED_OUT,
    TRANSFER_CANCELLED,
    TRANSFER_STALL,
    TRANSFER_NO_DEVICE,
    TRANSFER_OVERFLOW,
    # pylint: enable=undefined-variable
))

def DEFAULT_ASYNC_TRANSFER_ERROR_CALLBACK(_):
    return False

def create_binary_buffer(init_or_size):
    """
    ctypes.create_string_buffer variant which does not add a trailing null
    when init_or_size is not a size.
    """
    # As per ctypes.create_string_buffer:
    # - int is a length
    # - bytes is an initialiser
    if isinstance(init_or_size, int):
        init_or_size = bytearray(init_or_size)
    return create_initialised_buffer(init_or_size)

class _LibUSB1Finalizer: # pylint: disable=too-few-public-methods
    __finalizer_id_generator = itertools.count()

    def __init__(self):
        self._finalizer_dict = {}

    @staticmethod
    def __finalize(handle, pop, func, kw):
        try:
            func(**kw)
        finally:
            pop(handle)

    def _getFinalizer(self, obj, func, **kw):
        handle = next(self.__finalizer_id_generator)
        finalizer_dict = self._finalizer_dict
        finalizer_dict[handle] = finalizer = weakref.finalize(
            obj,
            functools.partial(
                self.__finalize, # Note: static method
                handle=handle,
                pop=finalizer_dict.pop,
                func=func,
                kw=kw,
            ),
        )
        return finalizer

def create_initialised_buffer(init):
    # raises if init is an integer - this is intentional
    string_type = c_char * len(init)
    try:
        # zero-copy if init is a writable buffer
        return string_type.from_buffer(init), init
    # cpython (3.5, 3.9) raises TypeError, pypy 5.4.1 raises ValueError
    except (TypeError, ValueError):
        # create our own writable buffer
        init = bytearray(init)
        return string_type.from_buffer(init), init

class DoomedTransferError(Exception):
    """Exception raised when altering/submitting a doomed transfer."""

class USBTransfer:
    """
    USB asynchronous transfer control & data.

    All modification methods will raise if called on a submitted transfer.
    Methods noted as "should not be called on a submitted transfer" will not
    prevent you from reading, but returned value is unspecified.

    Note on user_data: because of pypy's current ctype restrictions, user_data
    is not provided to C level, but is managed purely in python. It should
    change nothing for you, unless you are looking at underlying C transfer
    structure - which you should never have to.
    """
    __transfer = None
    __initialized = False
    __submitted_dict = {}
    __callback = None
    # Just to silence pylint watnings, this attribute gets overridden after
    # class definition.
    __ctypesCallbackWrapper = None
    __doomed = False
    __user_data = None
    __transfer_buffer = None
    __transfer_py_buffer = None

    def __init__(
        self,
        context,
        handle,
        iso_packets,
        before_submit,
        after_completion,
        getFinalizer,
        short_is_error,
        add_zero_packet,
    ):
        """
        You should not instanciate this class directly.
        Call "getTransfer" method on an USBDeviceHandle instance to get
        instances of this class.
        """
        if iso_packets < 0:
            raise ValueError(
                'Cannot request a negative number of iso packets.'
            )
        self.__handle = handle
        self.__before_submit = before_submit
        self.__after_completion = after_completion
        self.__num_iso_packets = iso_packets
        transfer = libusb1.libusb_alloc_transfer(iso_packets)
        if not transfer:
            # pylint: disable=undefined-variable
            raise USBErrorNoMem
            # pylint: enable=undefined-variable
        self.__transfer = transfer
        self.setShortIsError(short_is_error)
        self.setAddZeroPacket(add_zero_packet)
        self.__close = getFinalizer(
            self,
            self.__close, # Note: class method
            transfer=transfer,
            context=context,
            libusb_free_transfer=libusb1.libusb_free_transfer,
            libusb_cancel_transfer=libusb1.libusb_cancel_transfer,
        )

    def close(self):
        """
        Break reference cycles to allow instance to be garbage-collected.
        Raises if called on a submitted transfer.
        """
        if self.isSubmitted():
            raise ValueError('Cannot close a submitted transfer')
        self.doom()
        self.__initialized = False
        # Break possible external reference cycles
        self.__callback = None
        self.__user_data = None
        # For some reason, overwriting callback is not enough to remove this
        # reference cycle - though sometimes it works:
        #   self -> self.__dict__ -> libusb_transfer -> dict[x] -> dict[x] ->
        #   CThunkObject -> __callbackWrapper -> self
        # So free transfer altogether.
        self.__close()
        self.__transfer = None
        # pylint: disable=unused-private-member
        self.__transfer_buffer = None
        # pylint: enable=unused-private-member
        # Break USBDeviceHandle reference cycle
        self.__before_submit = None
        self.__after_completion = None

    @classmethod
    def __close( # pylint: disable=method-hidden
        cls,
        transfer,
        context,
        libusb_free_transfer,
        libusb_cancel_transfer,

        # pylint: disable=undefined-variable
        USBErrorInterrupted_=USBErrorInterrupted,
        # pylint: enable=undefined-variable
    ):
        isSubmitted = cls.__isSubmitted
        # Unlikely to be true if we are triggered by object destruction
        # (cls.__submitted_dict is precisely here to prevent collection of
        # submitted transfers).
        # And if we are called by the user, then they should have the ability
        # to cancel the transfer cleanly before closing it.
        if isSubmitted(transfer):
            libusb_cancel_transfer(transfer)
            while isSubmitted(transfer):
                try:
                    context.handleEvents()
                except USBErrorInterrupted_:
                    pass
        libusb_free_transfer(transfer)

    def doom(self):
        """
        Prevent transfer from being submitted again.
        """
        self.__doomed = True

    @classmethod
    # pylint: disable=unused-private-member
    def __callbackWrapper(cls, transfer_p):
    # pylint: enable=unused-private-member
        """
        Makes it possible for user-provided callback to alter transfer when
        fired (ie, mark transfer as not submitted upon call).
        """
        # pylint: disable=protected-access
        self = cls.__submitted_dict.pop(addressof(transfer_p.contents))
        self.__after_completion(self)
        callback = self.__callback
        if callback is not None:
            callback(self)
        if self.__doomed:
            self.close()
        # pylint: enable=protected-access

    def setCallback(self, callback):
        """
        Change transfer's callback.
        """
        self.__callback = callback

    def getCallback(self):
        """
        Get currently set callback.
        """
        return self.__callback

    def setControl(
            self, request_type, request, value, index, buffer_or_len,
            callback=None, user_data=None, timeout=0):
        """
        Setup transfer for control use.

        request_type, request, value, index
            See USBDeviceHandle.controlWrite.
            request_type defines transfer direction (see
            ENDPOINT_OUT and ENDPOINT_IN)).
        buffer_or_len
            Either bytes (when sending data), or expected data length (when
            receiving data).
        callback
            Callback function to be invoked on transfer completion.
            Called with transfer as parameter, return value ignored.
        user_data
            User data to pass to callback function.
        timeout
            Transfer timeout in milliseconds. 0 to disable.
        """
        if self.isSubmitted():
            raise ValueError('Cannot alter a submitted transfer')
        if self.__doomed:
            raise DoomedTransferError('Cannot reuse a doomed transfer')
        if isinstance(buffer_or_len, int):
            length = buffer_or_len
            # pylint: disable=undefined-variable
            string_buffer, transfer_py_buffer = create_binary_buffer(
                length + CONTROL_SETUP_SIZE,
            )
            # pylint: enable=undefined-variable
        else:
            length = len(buffer_or_len)
            string_buffer, transfer_py_buffer = create_binary_buffer(
                CONTROL_SETUP + buffer_or_len,
            )
        self.__initialized = False
        # pylint: disable=unused-private-member
        self.__transfer_buffer = string_buffer
        # pylint: enable=unused-private-member
        # pylint: disable=undefined-variable
        self.__transfer_py_buffer = memoryview(
            transfer_py_buffer,
        )[CONTROL_SETUP_SIZE:]
        # pylint: enable=undefined-variable
        self.__user_data = user_data
        libusb1.libusb_fill_control_setup(
            string_buffer, request_type, request, value, index, length)
        libusb1.libusb_fill_control_transfer(
            self.__transfer, self.__handle, string_buffer,
            self.__ctypesCallbackWrapper, None, timeout)
        self.__callback = callback
        self.__initialized = True

    def setBulk(
            self, endpoint, buffer_or_len, callback=None, user_data=None,
            timeout=0):
        """
        Setup transfer for bulk use.

        endpoint
            Endpoint to submit transfer to. Defines transfer direction (see
            ENDPOINT_OUT and ENDPOINT_IN)).
        buffer_or_len
            Either bytes (when sending data), or expected data length (when
            receiving data)
            To avoid memory copies, use an object implementing the writeable
            buffer interface (ex: bytearray).
        callback
            Callback function to be invoked on transfer completion.
            Called with transfer as parameter, return value ignored.
        user_data
            User data to pass to callback function.
        timeout
            Transfer timeout in milliseconds. 0 to disable.
        """
        if self.isSubmitted():
            raise ValueError('Cannot alter a submitted transfer')
        if self.__doomed:
            raise DoomedTransferError('Cannot reuse a doomed transfer')
        string_buffer, self.__transfer_py_buffer = create_binary_buffer(
            buffer_or_len
        )
        self.__initialized = False
        # pylint: disable=unused-private-member
        self.__transfer_buffer = string_buffer
        # pylint: enable=unused-private-member
        self.__user_data = user_data
        libusb1.libusb_fill_bulk_transfer(
            self.__transfer, self.__handle, endpoint, string_buffer,
            sizeof(string_buffer), self.__ctypesCallbackWrapper, None, timeout)
        self.__callback = callback
        self.__initialized = True

    def setInterrupt(
            self, endpoint, buffer_or_len, callback=None, user_data=None,
            timeout=0):
        """
        Setup transfer for interrupt use.

        endpoint
            Endpoint to submit transfer to. Defines transfer direction (see
            ENDPOINT_OUT and ENDPOINT_IN)).
        buffer_or_len
            Either bytes (when sending data), or expected data length (when
            receiving data)
            To avoid memory copies, use an object implementing the writeable
            buffer interface (ex: bytearray).
        callback
            Callback function to be invoked on transfer completion.
            Called with transfer as parameter, return value ignored.
        user_data
            User data to pass to callback function.
        timeout
            Transfer timeout in milliseconds. 0 to disable.
        """
        if self.isSubmitted():
            raise ValueError('Cannot alter a submitted transfer')
        if self.__doomed:
            raise DoomedTransferError('Cannot reuse a doomed transfer')
        string_buffer, self.__transfer_py_buffer = create_binary_buffer(
            buffer_or_len
        )
        self.__initialized = False
        # pylint: disable=unused-private-member
        self.__transfer_buffer = string_buffer
        # pylint: enable=unused-private-member
        self.__user_data = user_data
        libusb1.libusb_fill_interrupt_transfer(
            self.__transfer, self.__handle, endpoint, string_buffer,
            sizeof(string_buffer), self.__ctypesCallbackWrapper, None, timeout)
        self.__callback = callback
        self.__initialized = True

    def setIsochronous(
            self, endpoint, buffer_or_len, callback=None,
            user_data=None, timeout=0, iso_transfer_length_list=None):
        """
        Setup transfer for isochronous use.

        endpoint
            Endpoint to submit transfer to. Defines transfer direction (see
            ENDPOINT_OUT and ENDPOINT_IN)).
        buffer_or_len
            Either bytes (when sending data), or expected data length (when
            receiving data)
            To avoid memory copies, use an object implementing the writeable
            buffer interface (ex: bytearray).
        callback
            Callback function to be invoked on transfer completion.
            Called with transfer as parameter, return value ignored.
        user_data
            User data to pass to callback function.
        timeout
            Transfer timeout in milliseconds. 0 to disable.
        iso_transfer_length_list
            List of individual transfer sizes. If not provided, buffer_or_len
            will be divided evenly among available transfers if possible, and
            raise ValueError otherwise.
        """
        if self.isSubmitted():
            raise ValueError('Cannot alter a submitted transfer')
        num_iso_packets = self.__num_iso_packets
        if num_iso_packets == 0:
            raise TypeError(
                'This transfer canot be used for isochronous I/O. '
                'You must get another one with a non-zero iso_packets '
                'parameter.'
            )
        if self.__doomed:
            raise DoomedTransferError('Cannot reuse a doomed transfer')
        string_buffer, transfer_py_buffer = create_binary_buffer(buffer_or_len)
        buffer_length = sizeof(string_buffer)
        if iso_transfer_length_list is None:
            iso_length, remainder = divmod(buffer_length, num_iso_packets)
            if remainder:
                raise ValueError(
                    f'Buffer size {buffer_length} cannot be evenly distributed '
                    f'among {num_iso_packets} transfers',
                )
            iso_transfer_length_list = [iso_length] * num_iso_packets
        configured_iso_packets = len(iso_transfer_length_list)
        if configured_iso_packets > num_iso_packets:
            raise ValueError(
                f'Too many ISO transfer lengths ({configured_iso_packets}), '
                f'there are only {num_iso_packets} ISO transfers available',
            )
        if sum(iso_transfer_length_list) > buffer_length:
            raise ValueError(
                f'ISO transfers too long ({sum(iso_transfer_length_list)}), '
                f'there are only {buffer_length} bytes available',
            )
        transfer_p = self.__transfer
        self.__initialized = False
        # pylint: disable=unused-private-member
        self.__transfer_buffer = string_buffer
        # pylint: enable=unused-private-member
        self.__transfer_py_buffer = transfer_py_buffer
        self.__user_data = user_data
        libusb1.libusb_fill_iso_transfer(
            transfer_p, self.__handle, endpoint, string_buffer, buffer_length,
            configured_iso_packets, self.__ctypesCallbackWrapper, None,
            timeout)
        for length, iso_packet_desc in zip(
                iso_transfer_length_list,
                libusb1.get_iso_packet_list(transfer_p)):
            if length <= 0:
                raise ValueError(
                    'Negative/null length transfers are not possible.'
                )
            iso_packet_desc.length = length
        self.__callback = callback
        self.__initialized = True

    def getType(self):
        """
        Get transfer type.

        Returns one of:
            TRANSFER_TYPE_CONTROL
            TRANSFER_TYPE_ISOCHRONOUS
            TRANSFER_TYPE_BULK
            TRANSFER_TYPE_INTERRUPT
        """
        return self.__transfer.contents.type

    def getEndpoint(self):
        """
        Get endpoint.
        """
        return self.__transfer.contents.endpoint

    def getStatus(self):
        """
        Get transfer status.
        Should not be called on a submitted transfer.
        """
        return self.__transfer.contents.status

    def getActualLength(self):
        """
        Get actually transfered data length.
        Should not be called on a submitted transfer.
        """
        return self.__transfer.contents.actual_length

    def getBuffer(self):
        """
        Get data buffer content.
        Should not be called on a submitted transfer.
        """
        return self.__transfer_py_buffer

    def getUserData(self):
        """
        Retrieve user data provided on setup.
        """
        return self.__user_data

    def setUserData(self, user_data):
        """
        Change user data.
        """
        self.__user_data = user_data

    def getISOBufferList(self):
        """
        Get individual ISO transfer's buffer.
        Returns a list with one item per ISO transfer, with their
        individually-configured sizes.
        Returned list is consistent with getISOSetupList return value.
        Should not be called on a submitted transfer.

        See also iterISO.
        """
        transfer_p = self.__transfer
        transfer = transfer_p.contents
        # pylint: disable=undefined-variable
        if transfer.type != TRANSFER_TYPE_ISOCHRONOUS:
            # pylint: enable=undefined-variable
            raise TypeError(
                'This method cannot be called on non-iso transfers.'
            )
        return libusb1.get_iso_packet_buffer_list(transfer_p)

    def getISOSetupList(self):
        """
        Get individual ISO transfer's setup.
        Returns a list of dicts, each containing an individual ISO transfer
        parameters:
        - length
        - actual_length
        - status
        (see libusb1's API documentation for their signification)
        Returned list is consistent with getISOBufferList return value.
        Should not be called on a submitted transfer (except for 'length'
        values).
        """
        transfer_p = self.__transfer
        transfer = transfer_p.contents
        # pylint: disable=undefined-variable
        if transfer.type != TRANSFER_TYPE_ISOCHRONOUS:
            # pylint: enable=undefined-variable
            raise TypeError(
                'This method cannot be called on non-iso transfers.'
            )
        return [
            {
                'length': x.length,
                'actual_length': x.actual_length,
                'status': x.status,
            }
            for x in libusb1.get_iso_packet_list(transfer_p)
        ]

    def iterISO(self):
        """
        Generator yielding (status, buffer) for each isochornous transfer.
        buffer is truncated to actual_length.
        This is more efficient than calling both getISOBufferList and
        getISOSetupList when receiving data.
        Should not be called on a submitted transfer.
        """
        transfer_p = self.__transfer
        transfer = transfer_p.contents
        # pylint: disable=undefined-variable
        if transfer.type != TRANSFER_TYPE_ISOCHRONOUS:
            # pylint: enable=undefined-variable
            raise TypeError(
                'This method cannot be called on non-iso transfers.'
            )
        buffer_position = transfer.buffer
        for iso_transfer in libusb1.get_iso_packet_list(transfer_p):
            yield (
                iso_transfer.status,
                libusb1.buffer_at(buffer_position, iso_transfer.actual_length),
            )
            buffer_position += iso_transfer.length

    def setBuffer(self, buffer_or_len):
        """
        Replace buffer with a new one.
        Allows resizing read buffer and replacing data sent.
        Note: resizing is not allowed for isochronous buffer (use
        setIsochronous).
        Note: disallowed on control transfers (use setControl).
        """
        if self.isSubmitted():
            raise ValueError('Cannot alter a submitted transfer')
        transfer = self.__transfer.contents
        # pylint: disable=undefined-variable
        if transfer.type == TRANSFER_TYPE_CONTROL:
            # pylint: enable=undefined-variable
            raise ValueError(
                'To alter control transfer buffer, use setControl'
            )
        buff, transfer_py_buffer = create_binary_buffer(buffer_or_len)
        # pylint: disable=undefined-variable
        if transfer.type == TRANSFER_TYPE_ISOCHRONOUS and \
                sizeof(buff) != transfer.length:
            # pylint: enable=undefined-variable
            raise ValueError(
                'To alter isochronous transfer buffer length, use '
                'setIsochronous'
            )
        # pylint: disable=unused-private-member
        self.__transfer_buffer = buff
        # pylint: enable=unused-private-member
        self.__transfer_py_buffer = transfer_py_buffer
        transfer.buffer = cast(buff, c_void_p)
        transfer.length = sizeof(buff)

    def isShortAnError(self):
        """
        Returns whether the LIBUSB_TRANSFER_SHORT_NOT_OK flag is set on this
        transfer.
        """
        return bool(self.__transfer.contents.flags & libusb1.LIBUSB_TRANSFER_SHORT_NOT_OK)

    def setShortIsError(self, state):
        """
        state (bool)
            When true, LIBUSB_TRANSFER_SHORT_NOT_OK flag is set on this
            transfer.
            Otherwise, it is cleared.
        """
        if state:
            self.__transfer.contents.flags |= libusb1.LIBUSB_TRANSFER_SHORT_NOT_OK
        else:
            self.__transfer.contents.flags &= ~libusb1.LIBUSB_TRANSFER_SHORT_NOT_OK

    def isZeroPacketAdded(self):
        """
        Returns whether the LIBUSB_TRANSFER_ADD_ZERO_PACKET flag is set on this
        transfer.
        """
        return bool(self.__transfer.contents.flags & libusb1.LIBUSB_TRANSFER_ADD_ZERO_PACKET)

    def setAddZeroPacket(self, state):
        """
        state (bool)
            When true, LIBUSB_TRANSFER_ADD_ZERO_PACKET flag is set on this
            transfer.
            Otherwise, it is cleared.
        """
        if state:
            self.__transfer.contents.flags |= libusb1.LIBUSB_TRANSFER_ADD_ZERO_PACKET
        else:
            self.__transfer.contents.flags &= ~libusb1.LIBUSB_TRANSFER_ADD_ZERO_PACKET

    def isSubmitted(self):
        """
        Tells if this transfer is submitted and still pending.
        """
        transfer = self.__transfer
        return transfer is not None and self.__isSubmitted(transfer)

    @classmethod
    def __isSubmitted(cls, transfer):
        return addressof(transfer.contents) in cls.__submitted_dict

    def submit(self):
        """
        Submit transfer for asynchronous handling.
        """
        if self.isSubmitted():
            raise ValueError('Cannot submit a submitted transfer')
        if not self.__initialized:
            raise ValueError(
                'Cannot submit a transfer until it has been initialized'
            )
        if self.__doomed:
            raise DoomedTransferError('Cannot submit doomed transfer')
        self.__before_submit(self)
        transfer = self.__transfer
        assert transfer is not None
        self.__submitted_dict[addressof(transfer.contents)] = self
        result = libusb1.libusb_submit_transfer(transfer)
        if result:
            self.__after_completion(self)
            self.__submitted_dict.pop(addressof(transfer.contents))
            raiseUSBError(result)

    def cancel(self):
        """
        Cancel transfer.
        Note: cancellation happens asynchronously, so you must wait for
        TRANSFER_CANCELLED.
        """
        if not self.isSubmitted():
            # XXX: Workaround for a bug reported on libusb 1.0.8: calling
            # libusb_cancel_transfer on a non-submitted transfer might
            # trigger a segfault.
            raise USBErrorNotFound # pylint: disable=undefined-variable
        mayRaiseUSBError(libusb1.libusb_cancel_transfer(self.__transfer))

# XXX: This is very unsightly, but I do not see another way of declaring within
# class body both the class method and its ctypes function pointer.
# pylint: disable=protected-access,no-member
USBTransfer._USBTransfer__ctypesCallbackWrapper = libusb1.libusb_transfer_cb_fn_p(
    USBTransfer._USBTransfer__callbackWrapper,
)
# pylint: enable=protected-access,no-member

class USBTransferHelper:
    """
    Simplifies subscribing to the same transfer over and over, and callback
    handling:
    - no need to read event status to execute apropriate code, just setup
      different functions for each status code
    - just return True instead of calling submit
    - no need to check if transfer is doomed before submitting it again,
      DoomedTransferError is caught.

    Callbacks used in this class must follow the callback API described in
    USBTransfer, and are expected to return a boolean:
    - True if transfer is to be submitted again (to receive/send more data)
    - False otherwise

    Note: as per libusb1 specifications, isochronous transfer global state
    might be TRANSFER_COMPLETED although some individual packets might
    have an error status. You can check individual packet status by calling
    getISOSetupList on transfer object in your callback.
    """
    def __init__(self, transfer=None):
        """
        Create a transfer callback dispatcher.

        transfer parameter is deprecated. If provided, it will be equivalent
        to:
            helper = USBTransferHelper()
            transfer.setCallback(helper)
        and also allows using deprecated methods on this class (otherwise,
        they raise AttributeError).
        """
        if transfer is not None:
            # Deprecated: to drop
            self.__transfer = transfer
            transfer.setCallback(self)
        self.__event_callback_dict = {}
        self.__errorCallback = DEFAULT_ASYNC_TRANSFER_ERROR_CALLBACK

    def submit(self):
        """
        Submit the asynchronous read request.
        Deprecated. Use submit on transfer.
        """
        # Deprecated: to drop
        self.__transfer.submit()

    def cancel(self):
        """
        Cancel a pending read request.
        Deprecated. Use cancel on transfer.
        """
        # Deprecated: to drop
        self.__transfer.cancel()

    def setEventCallback(self, event, callback):
        """
        Set a function to call for a given event.
        event must be one of:
            TRANSFER_COMPLETED
            TRANSFER_ERROR
            TRANSFER_TIMED_OUT
            TRANSFER_CANCELLED
            TRANSFER_STALL
            TRANSFER_NO_DEVICE
            TRANSFER_OVERFLOW
        """
        if event not in EVENT_CALLBACK_SET:
            raise ValueError(f'Unknown event {event!r}.')
        self.__event_callback_dict[event] = callback

    def setDefaultCallback(self, callback):
        """
        Set the function to call for event which don't have a specific callback
        registered.
        The initial default callback does nothing and returns False.
        """
        self.__errorCallback = callback

    def getEventCallback(self, event, default=None):
        """
        Return the function registered to be called for given event identifier.
        """
        return self.__event_callback_dict.get(event, default)

    def __call__(self, transfer):
        """
        Callback to set on transfers.
        """
        if self.getEventCallback(transfer.getStatus(), self.__errorCallback)(
                transfer):
            try:
                transfer.submit()
            except DoomedTransferError:
                pass

    def isSubmited(self):
        """
        Returns whether this reader is currently waiting for an event.
        Deprecatd. Use isSubmitted on transfer.
        """
        # Deprecated: to drop
        return self.__transfer.isSubmitted()

class USBPoller:
    """
    Class allowing integration of USB event polling in a file-descriptor
    monitoring event loop.

    WARNING: Do not call "poll" from several threads concurently. Do not use
    synchronous USB transfers in a thread while "poll" is running. Doing so
    will result in unnecessarily long pauses in some threads. Opening and/or
    closing devices while polling can cause race conditions to occur.
    """
    def __init__(self, context, poller):
        """
        Create a poller for given context.
        Warning: it will not check if another poller instance was already
        present for that context, and will replace it.

        poller is a polling instance implementing the following methods:
        - register(fd, event_flags)
          event_flags have the same meaning as in poll API (POLLIN & POLLOUT)
        - unregister(fd)
        - poll(timeout)
          timeout being a float in seconds, or negative/None if there is no
          timeout.
          It must return a list of (descriptor, event) pairs.
        Note: USBPoller is itself a valid poller.
        Note2: select.poll uses a timeout in milliseconds, for some reason
        (all other select.* classes use seconds for timeout), so you should
        wrap it to convert & round/truncate timeout.
        """
        self.__context = context
        self.__poller = poller
        self.__fd_set = set()
        context.setPollFDNotifiers(self._registerFD, self._unregisterFD)
        for fd, events in context.getPollFDList():
            self._registerFD(fd, events)

    def __del__(self):
        self.__context.setPollFDNotifiers(None, None)

    def poll(self, timeout=None):
        """
        Poll for events.
        timeout can be a float in seconds, or None for no timeout.
        Returns a list of (descriptor, event) pairs.
        """
        next_usb_timeout = self.__context.getNextTimeout()
        if timeout is None or timeout < 0:
            usb_timeout = next_usb_timeout
        elif next_usb_timeout:
            usb_timeout = min(next_usb_timeout, timeout)
        else:
            usb_timeout = timeout
        event_list = self.__poller.poll(usb_timeout)
        if event_list:
            fd_set = self.__fd_set
            result = [(x, y) for x, y in event_list if x not in fd_set]
            if len(result) != len(event_list):
                self.__context.handleEventsTimeout()
        else:
            result = event_list
            self.__context.handleEventsTimeout()
        return result

    def register(self, fd, events):
        """
        Register an USB-unrelated fd to poller.
        Convenience method.
        """
        if fd in self.__fd_set:
            raise ValueError(
                'This fd is a special USB event fd, it cannot be polled.'
            )
        self.__poller.register(fd, events)

    def unregister(self, fd):
        """
        Unregister an USB-unrelated fd from poller.
        Convenience method.
        """
        if fd in self.__fd_set:
            raise ValueError(
                'This fd is a special USB event fd, it must stay registered.'
            )
        self.__poller.unregister(fd)

    # pylint: disable=unused-argument
    def _registerFD(self, fd, events, user_data=None):
        self.register(fd, events)
        self.__fd_set.add(fd)
    # pylint: enable=unused-argument

    # pylint: disable=unused-argument
    def _unregisterFD(self, fd, user_data=None):
        self.__fd_set.discard(fd)
        self.unregister(fd)
    # pylint: enable=unused-argument

class _ReleaseInterface:
    def __init__(self, handle, interface):
        self._handle = handle
        self._interface = interface

    def __enter__(self):
        # USBDeviceHandle.claimInterface already claimed the interface.
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._handle.releaseInterface(self._interface)

class USBDeviceHandle(_LibUSB1Finalizer):
    """
    Represents an opened USB device.
    """
    __handle = None

    def __init__(
        self,
        context,
        handle,
        device,
        getFinalizer,
        can_close_device,
    ):
        """
        You should not instanciate this class directly.
        Call "open" method on an USBDevice instance to get an USBDeviceHandle
        instance.
        """
        super().__init__()
        self.__context = context
        # Strong references to inflight transfers so they do not get freed
        # even if user drops all strong references to them. If this instance
        # is garbage-collected, we close all transfers, so it's fine.
        inflight = set()
        # XXX: For some reason, doing self.__inflight.{add|remove} inside
        # getTransfer causes extra intermediate python objects for each
        # allocated transfer. Storing them as properties solves this. Found
        # with objgraph.
        self.__inflight_add = inflight.add
        self.__inflight_remove = inflight.remove
        self.__handle = handle
        self.__device = device
        self.close = getFinalizer(
            self,
            self.close, # Note: static method
            context=context,
            handle=handle,
            device=(
                device
                if can_close_device else
                None
            ),
            inflight=inflight,
            finalizer_dict=self._finalizer_dict,
            libusb_close=libusb1.libusb_close,
        )

    @staticmethod
    def close( # pylint: disable=method-hidden
        context,
        handle,
        device,
        inflight,
        finalizer_dict,
        libusb_close,

        set_=set,
        # pylint: disable=undefined-variable
        USBErrorNotFound_=USBErrorNotFound,
        USBErrorNoDevice_=USBErrorNoDevice,
        USBErrorInterrupted_=USBErrorInterrupted,
        # pylint: enable=undefined-variable
    ):
        """
        Close this handle. If not called explicitely, will be called by
        destructor.

        This method cancels any in-flight transfer when it is called. As
        cancellation is not immediate, this method needs to let libusb handle
        events until transfers are actually cancelled.
        In multi-threaded programs, this can lead to stalls. To avoid this,
        do not close nor let GC collect a USBDeviceHandle which has in-flight
        transfers.
        """
        cancelled_set = set_()
        while inflight:
            for transfer in tuple(inflight):
                if transfer not in cancelled_set:
                    try:
                        transfer.cancel()
                    except (USBErrorNotFound_, USBErrorNoDevice_):
                        pass
                    cancelled_set.add(transfer)
            try:
                context.handleEvents()
            except USBErrorInterrupted_:
                pass
        while finalizer_dict:
            for finalizer_handle, finalizer in list(finalizer_dict.items()):
                finalizer()
                assert finalizer_handle not in finalizer_dict
        if device is not None:
            device.close()
        libusb_close(handle)

    def getDevice(self):
        """
        Get an USBDevice instance for the device accessed through this handle,
        to access to the descriptors available in OS cache.
        """
        return self.__device

    def getConfiguration(self):
        """
        Get the current configuration number for this device.
        """
        configuration = c_int()
        mayRaiseUSBError(libusb1.libusb_get_configuration(
            self.__handle, byref(configuration),
        ))
        return configuration.value

    def setConfiguration(self, configuration):
        """
        Set the configuration number for this device.
        """
        mayRaiseUSBError(
            libusb1.libusb_set_configuration(self.__handle, configuration),
        )

    def getManufacturer(self):
        """
        Get device's manufaturer name.
        """
        return self.getASCIIStringDescriptor(
            self.__device.device_descriptor.iManufacturer,
        )

    def getProduct(self):
        """
        Get device's product name.
        """
        return self.getASCIIStringDescriptor(
            self.__device.device_descriptor.iProduct,
        )

    def getSerialNumber(self):
        """
        Get device's serial number.
        """
        return self.getASCIIStringDescriptor(
            self.__device.device_descriptor.iSerialNumber,
        )

    def claimInterface(self, interface):
        """
        Claim (= get exclusive access to) given interface number. Required to
        receive/send data.

        Can be used as a context manager:
            with handle.claimInterface(0):
                # do stuff
            # handle.releaseInterface(0) gets automatically called
        """
        mayRaiseUSBError(
            libusb1.libusb_claim_interface(self.__handle, interface),
        )
        return _ReleaseInterface(self, interface)

    def releaseInterface(self, interface):
        """
        Release interface, allowing another process to use it.
        """
        mayRaiseUSBError(
            libusb1.libusb_release_interface(self.__handle, interface),
        )

    def setInterfaceAltSetting(self, interface, alt_setting):
        """
        Set interface's alternative setting (both parameters are integers).
        """
        mayRaiseUSBError(libusb1.libusb_set_interface_alt_setting(
            self.__handle, interface, alt_setting,
        ))

    def clearHalt(self, endpoint):
        """
        Clear a halt state on given endpoint number.
        """
        mayRaiseUSBError(libusb1.libusb_clear_halt(self.__handle, endpoint))

    def resetDevice(self):
        """
        Reinitialise current device.
        Attempts to restore current configuration & alt settings.
        If this fails, will result in a device disconnect & reconnect, so you
        have to close current device and rediscover it (notified by an
        USBErrorNotFound exception).
        """
        mayRaiseUSBError(libusb1.libusb_reset_device(self.__handle))

    def kernelDriverActive(self, interface):
        """
        Tell whether a kernel driver is active on given interface number.
        """
        result = libusb1.libusb_kernel_driver_active(self.__handle, interface)
        if result == 0:
            return False
        if result == 1:
            return True
        raiseUSBError(result)
        return None # unreachable, to make pylint happy

    def detachKernelDriver(self, interface):
        """
        Ask kernel driver to detach from given interface number.
        """
        mayRaiseUSBError(
            libusb1.libusb_detach_kernel_driver(self.__handle, interface),
        )

    def attachKernelDriver(self, interface):
        """
        Ask kernel driver to re-attach to given interface number.
        """
        mayRaiseUSBError(
            libusb1.libusb_attach_kernel_driver(self.__handle, interface),
        )

    def setAutoDetachKernelDriver(self, enable):
        """
        Control automatic kernel driver detach.
        enable (bool)
            True to enable auto-detach, False to disable it.
        """
        mayRaiseUSBError(libusb1.libusb_set_auto_detach_kernel_driver(
            self.__handle, bool(enable),
        ))

    def getSupportedLanguageList(self):
        """
        Return a list of USB language identifiers (as integers) supported by
        current device for its string descriptors.

        Note: language identifiers seem (I didn't check them all...) very
        similar to windows language identifiers, so you may want to use
        locales.windows_locale to get an rfc3066 representation. The 5 standard
        HID language codes are missing though.
        """
        descriptor_string, _ = create_binary_buffer(STRING_LENGTH)
        result = libusb1.libusb_get_string_descriptor(
            self.__handle, 0, 0, descriptor_string, sizeof(descriptor_string),
        )
        # pylint: disable=undefined-variable
        if result == ERROR_PIPE:
            # pylint: enable=undefined-variable
            # From libusb_control_transfer doc:
            # control request not supported by the device
            return []
        mayRaiseUSBError(result)
        langid_list = cast(descriptor_string, POINTER(c_uint16))
        return [
            libusb1.libusb_le16_to_cpu(langid_list[offset])
            for offset in range(1, cast(descriptor_string, POINTER(c_ubyte))[0] // 2)
        ]

    def getStringDescriptor(self, descriptor, lang_id, errors='strict'):
        """
        Fetch description string for given descriptor and in given language.
        Use getSupportedLanguageList to know which languages are available.
        Return value is a unicode string.
        Return None if there is no such descriptor on device.
        """
        if descriptor == 0:
            return None
        descriptor_string = bytearray(STRING_LENGTH)
        try:
            received = mayRaiseUSBError(libusb1.libusb_get_string_descriptor(
                self.__handle, descriptor, lang_id,
                create_binary_buffer(descriptor_string)[0],
                STRING_LENGTH,
            ))
        # pylint: disable=undefined-variable
        except USBErrorNotFound:
            # pylint: enable=undefined-variable
            return None
        # pylint: disable=undefined-variable
        if received < 2 or descriptor_string[1] != DT_STRING:
        # pylint: enable=undefined-variable
            raise ValueError('Invalid string descriptor')
        return descriptor_string[2:min(
            received,
            descriptor_string[0],
        )].decode('UTF-16-LE', errors=errors)

    def getASCIIStringDescriptor(self, descriptor, errors='strict'):
        """
        Fetch description string for given descriptor in first available
        language.
        Return value is a unicode string.
        Return None if there is no such descriptor on device.
        """
        if descriptor == 0:
            return None
        descriptor_string = bytearray(STRING_LENGTH)
        try:
            received = mayRaiseUSBError(libusb1.libusb_get_string_descriptor_ascii(
                self.__handle, descriptor,
                create_binary_buffer(descriptor_string)[0],
                STRING_LENGTH,
            ))
        # pylint: disable=undefined-variable
        except USBErrorNotFound:
            # pylint: enable=undefined-variable
            return None
        return descriptor_string[:received].decode('ASCII', errors=errors)

    # Sync I/O

    def _controlTransfer(
            self, request_type, request, value, index, data, length, timeout):
        result = libusb1.libusb_control_transfer(
            self.__handle, request_type, request, value, index, data, length,
            timeout,
        )
        mayRaiseUSBError(result)
        return result

    def controlWrite(
            self, request_type, request, value, index, data, timeout=0):
        """
        Synchronous control write.
        request_type: request type bitmask (bmRequestType), see
          constants TYPE_* and RECIPIENT_*.
        request: request id (some values are standard).
        value, index, data: meaning is request-dependent.
        timeout: in milliseconds, how long to wait for device acknowledgement.
          Set to 0 to disable.

        To avoid memory copies, use an object implementing the writeable buffer
        interface (ex: bytearray) for the "data" parameter.

        Returns the number of bytes actually sent.
        """
        # pylint: disable=undefined-variable
        request_type = (request_type & ~ENDPOINT_DIR_MASK) | ENDPOINT_OUT
        # pylint: enable=undefined-variable
        data, _ = create_initialised_buffer(data)
        return self._controlTransfer(request_type, request, value, index, data,
                                     sizeof(data), timeout)

    def controlRead(
            self, request_type, request, value, index, length, timeout=0):
        """
        Synchronous control read.
        timeout: in milliseconds, how long to wait for data. Set to 0 to
          disable.
        See controlWrite for other parameters description.

        To avoid memory copies, use an object implementing the writeable buffer
        interface (ex: bytearray) for the "data" parameter.

        Returns received data.
        """
        # pylint: disable=undefined-variable
        request_type = (request_type & ~ENDPOINT_DIR_MASK) | ENDPOINT_IN
        # pylint: enable=undefined-variable
        data, data_buffer = create_binary_buffer(length)
        transferred = self._controlTransfer(
            request_type, request, value, index, data, length, timeout,
        )
        return data_buffer[:transferred]

    def _bulkTransfer(self, endpoint, data, length, timeout):
        transferred = c_int()
        try:
            mayRaiseUSBError(libusb1.libusb_bulk_transfer(
                self.__handle, endpoint, data, length, byref(transferred), timeout,
            ))
        # pylint: disable=undefined-variable
        except USBErrorTimeout as exception:
            # pylint: enable=undefined-variable
            exception.transferred = transferred.value
            raise
        return transferred.value

    def bulkWrite(self, endpoint, data, timeout=0):
        """
        Synchronous bulk write.
        endpoint: endpoint to send data to.
        data: data to send.
        timeout: in milliseconds, how long to wait for device acknowledgement.
          Set to 0 to disable.

        To avoid memory copies, use an object implementing the writeable buffer
        interface (ex: bytearray) for the "data" parameter.

        Returns the number of bytes actually sent.

        May raise an exception from the USBError family. USBErrorTimeout
        exception has a "transferred" property giving the number of bytes sent
        up to the timeout.
        """
        # pylint: disable=undefined-variable
        endpoint = (endpoint & ~ENDPOINT_DIR_MASK) | ENDPOINT_OUT
        # pylint: enable=undefined-variable
        data, _ = create_initialised_buffer(data)
        return self._bulkTransfer(endpoint, data, sizeof(data), timeout)

    def bulkRead(self, endpoint, length, timeout=0):
        """
        Synchronous bulk read.
        timeout: in milliseconds, how long to wait for data. Set to 0 to
          disable.
        See bulkWrite for other parameters description.

        To avoid memory copies, use an object implementing the writeable buffer
        interface (ex: bytearray) for the "data" parameter.

        Returns received data.

        May raise an exception from the USBError family. USBErrorTimeout
        exception has a "received" property giving the bytes received up to the
        timeout.
        """
        # pylint: disable=undefined-variable
        endpoint = (endpoint & ~ENDPOINT_DIR_MASK) | ENDPOINT_IN
        # pylint: enable=undefined-variable
        data, data_buffer = create_binary_buffer(length)
        try:
            transferred = self._bulkTransfer(endpoint, data, length, timeout)
        # pylint: disable=undefined-variable
        except USBErrorTimeout as exception:
            # pylint: enable=undefined-variable
            exception.received = data_buffer[:exception.transferred]
            raise
        return data_buffer[:transferred]

    def _interruptTransfer(self, endpoint, data, length, timeout):
        transferred = c_int()
        try:
            mayRaiseUSBError(libusb1.libusb_interrupt_transfer(
                self.__handle,
                endpoint,
                data,
                length,
                byref(transferred),
                timeout,
            ))
        # pylint: disable=undefined-variable
        except USBErrorTimeout as exception:
            # pylint: enable=undefined-variable
            exception.transferred = transferred.value
            raise
        return transferred.value

    def interruptWrite(self, endpoint, data, timeout=0):
        """
        Synchronous interrupt write.
        endpoint: endpoint to send data to.
        data: data to send.
        timeout: in milliseconds, how long to wait for device acknowledgement.
          Set to 0 to disable.

        To avoid memory copies, use an object implementing the writeable buffer
        interface (ex: bytearray) for the "data" parameter.

        Returns the number of bytes actually sent.

        May raise an exception from the USBError family. USBErrorTimeout
        exception has a "transferred" property giving the number of bytes sent
        up to the timeout.
        """
        # pylint: disable=undefined-variable
        endpoint = (endpoint & ~ENDPOINT_DIR_MASK) | ENDPOINT_OUT
        # pylint: enable=undefined-variable
        data, _ = create_initialised_buffer(data)
        return self._interruptTransfer(endpoint, data, sizeof(data), timeout)

    def interruptRead(self, endpoint, length, timeout=0):
        """
        Synchronous interrupt write.
        timeout: in milliseconds, how long to wait for data. Set to 0 to
          disable.
        See interruptWrite for other parameters description.

        To avoid memory copies, use an object implementing the writeable buffer
        interface (ex: bytearray) for the "data" parameter.

        Returns received data.

        May raise an exception from the USBError family. USBErrorTimeout
        exception has a "received" property giving the bytes received up to the
        timeout.
        """
        # pylint: disable=undefined-variable
        endpoint = (endpoint & ~ENDPOINT_DIR_MASK) | ENDPOINT_IN
        # pylint: enable=undefined-variable
        data, data_buffer = create_binary_buffer(length)
        try:
            transferred = self._interruptTransfer(
                endpoint,
                data,
                length,
                timeout,
            )
        # pylint: disable=undefined-variable
        except USBErrorTimeout as exception:
            # pylint: enable=undefined-variable
            exception.received = data_buffer[:exception.transferred]
            raise
        return data_buffer[:transferred]

    def getTransfer(self, iso_packets=0, short_is_error=False, add_zero_packet=False):
        """
        Get an USBTransfer instance for asynchronous use.
        iso_packets: the number of isochronous transfer descriptors to
          allocate.
        short_is_error: When true, short frames are reported as errors.
        add_zero_packet: When true, transfers of a multiple of the endpoint
          size are followed by a zero-length packet.
        """
        return USBTransfer(
            context=self.__context,
            handle=self.__handle,
            iso_packets=iso_packets,
            before_submit=self.__inflight_add,
            after_completion=self.__inflight_remove,
            getFinalizer=self._getFinalizer,
            short_is_error=short_is_error,
            add_zero_packet=add_zero_packet,
        )

class USBConfiguration:
    def __init__(self, context, config, device_speed):
        """
        You should not instanciate this class directly.
        Call USBDevice methods to get instances of this class.
        """
        if not isinstance(config, libusb1.libusb_config_descriptor):
            raise TypeError('Unexpected descriptor type.')
        self.__config = config
        self.__context = context
        self.__device_speed = device_speed

    def getNumInterfaces(self):
        return self.__config.bNumInterfaces

    __len__ = getNumInterfaces

    def getConfigurationValue(self):
        return self.__config.bConfigurationValue

    def getDescriptor(self):
        return self.__config.iConfiguration

    def getAttributes(self):
        return self.__config.bmAttributes

    def getMaxPower(self):
        """
        Returns device's power consumption in mA.

        USB descriptor is expressed in units of 2 mA when the device is operating in high-speed mode
        and in units of 8 mA when the device is operating in super-speed mode. This function scales
        the descriptor value appropriately.
        """
        # pylint: disable=undefined-variable
        return self.__config.MaxPower * (8 if self.__device_speed == SPEED_SUPER else 2)
        # pylint: enable=undefined-variable

    def getExtra(self):
        """
        Returns a list of extra (non-basic) descriptors (DFU, HID, ...).
        """
        return libusb1.get_extra(self.__config)

    def __iter__(self):
        """
        Iterates over interfaces available in this configuration, yielding
        USBInterface instances.
        """
        context = self.__context
        interface_list = self.__config.interface
        for interface_num in range(self.getNumInterfaces()):
            yield USBInterface(context, interface_list[interface_num])

    # BBB
    iterInterfaces = __iter__

    def __getitem__(self, interface):
        """
        Returns an USBInterface instance.
        """
        if not isinstance(interface, int):
            raise TypeError('interface parameter must be an integer')
        if not 0 <= interface < self.getNumInterfaces():
            raise IndexError(f'No such interface: {interface!r}')
        return USBInterface(self.__context, self.__config.interface[interface])

class USBInterface:
    def __init__(self, context, interface):
        """
        You should not instanciate this class directly.
        Call USBConfiguration methods to get instances of this class.
        """
        if not isinstance(interface, libusb1.libusb_interface):
            raise TypeError('Unexpected descriptor type.')
        self.__interface = interface
        self.__context = context

    def getNumSettings(self):
        return self.__interface.num_altsetting

    __len__ = getNumSettings

    def __iter__(self):
        """
        Iterates over settings in this insterface, yielding
        USBInterfaceSetting instances.
        """
        context = self.__context
        alt_setting_list = self.__interface.altsetting
        for alt_setting_num in range(self.getNumSettings()):
            yield USBInterfaceSetting(
                context, alt_setting_list[alt_setting_num])

    # BBB
    iterSettings = __iter__

    def __getitem__(self, alt_setting):
        """
        Returns an USBInterfaceSetting instance.
        """
        if not isinstance(alt_setting, int):
            raise TypeError('alt_setting parameter must be an integer')
        if not 0 <= alt_setting < self.getNumSettings():
            raise IndexError(f'No such setting: {alt_setting!r}')
        return USBInterfaceSetting(
            self.__context, self.__interface.altsetting[alt_setting])

class USBInterfaceSetting:
    def __init__(self, context, alt_setting):
        """
        You should not instanciate this class directly.
        Call USBDevice or USBInterface methods to get instances of this class.
        """
        if not isinstance(alt_setting, libusb1.libusb_interface_descriptor):
            raise TypeError('Unexpected descriptor type.')
        self.__alt_setting = alt_setting
        self.__context = context

    def getNumber(self):
        return self.__alt_setting.bInterfaceNumber

    def getAlternateSetting(self):
        return self.__alt_setting.bAlternateSetting

    def getNumEndpoints(self):
        return self.__alt_setting.bNumEndpoints

    __len__ = getNumEndpoints

    def getClass(self):
        return self.__alt_setting.bInterfaceClass

    def getSubClass(self):
        return self.__alt_setting.bInterfaceSubClass

    def getClassTuple(self):
        """
        For convenience: class and subclass are probably often matched
        simultaneously.
        """
        alt_setting = self.__alt_setting
        return (alt_setting.bInterfaceClass, alt_setting.bInterfaceSubClass)

    # BBB
    getClassTupple = getClassTuple

    def getProtocol(self):
        return self.__alt_setting.bInterfaceProtocol

    def getDescriptor(self):
        return self.__alt_setting.iInterface

    def getExtra(self):
        return libusb1.get_extra(self.__alt_setting)

    def __iter__(self):
        """
        Iterates over endpoints in this interface setting , yielding
        USBEndpoint instances.
        """
        context = self.__context
        endpoint_list = self.__alt_setting.endpoint
        for endpoint_num in range(self.getNumEndpoints()):
            yield USBEndpoint(context, endpoint_list[endpoint_num])

    # BBB
    iterEndpoints = __iter__

    def __getitem__(self, endpoint):
        """
        Returns an USBEndpoint instance.
        """
        if not isinstance(endpoint, int):
            raise TypeError('endpoint parameter must be an integer')
        if not 0 <= endpoint < self.getNumEndpoints():
            raise ValueError(f'No such endpoint: {endpoint}')
        return USBEndpoint(
            self.__context, self.__alt_setting.endpoint[endpoint])

class USBEndpoint:
    def __init__(self, context, endpoint):
        if not isinstance(endpoint, libusb1.libusb_endpoint_descriptor):
            raise TypeError('Unexpected descriptor type.')
        self.__endpoint = endpoint
        # pylint: disable=unused-private-member
        self.__context = context
        # pylint: enable=unused-private-member

    def getAddress(self):
        return self.__endpoint.bEndpointAddress

    def getAttributes(self):
        return self.__endpoint.bmAttributes

    def getMaxPacketSize(self):
        return self.__endpoint.wMaxPacketSize

    def getInterval(self):
        return self.__endpoint.bInterval

    def getRefresh(self):
        return self.__endpoint.bRefresh

    def getSyncAddress(self):
        return self.__endpoint.bSynchAddress

    def getExtra(self):
        return libusb1.get_extra(self.__endpoint)

class USBDevice(_LibUSB1Finalizer):
    """
    Represents a USB device.

    Exposes USB descriptors which are available from OS without needing to get
    a USBDeviceHandle: device descriptor, configuration descriptors, interface
    descriptors, setting descritptors, endpoint descriptors.
    """

    __configuration_descriptor_list = ()
    __device_handle = None

    def __init__(
        self,
        context,
        device_p,
        getFinalizer,
        can_load_configuration,
        can_change_refcount,
        handle_p,
    ):
        """
        You should not instanciate this class directly.
        Call USBContext methods to receive instances of this class.
        """
        super().__init__()
        self.__context = context
        self.__configuration_descriptor_list = descriptor_list = []
        if can_change_refcount:
            libusb1.libusb_ref_device(device_p)
        self.close = getFinalizer(
            self,
            self.close, # Note: static method
            device_p=(
                device_p
                if can_change_refcount else
                None
            ),
            finalizer_dict=self._finalizer_dict,
            descriptor_list=descriptor_list,
            libusb_unref_device=libusb1.libusb_unref_device,
            libusb_free_config_descriptor=libusb1.libusb_free_config_descriptor,
        )
        self.device_p = device_p
        # Fetch device descriptor
        # Note: if this is made lazy, access errors will happen later, breaking
        # getDeviceIterator exception handling.
        device_descriptor = libusb1.libusb_device_descriptor()
        result = libusb1.libusb_get_device_descriptor(
            device_p, byref(device_descriptor))
        mayRaiseUSBError(result)
        self.device_descriptor = device_descriptor
        if can_load_configuration:
            append = descriptor_list.append
            for configuration_id in range(
                    self.device_descriptor.bNumConfigurations):
                config = libusb1.libusb_config_descriptor_p()
                result = libusb1.libusb_get_config_descriptor(
                    device_p, configuration_id, byref(config))
                # pylint: disable=undefined-variable
                if result == ERROR_NOT_FOUND:
                # pylint: enable=undefined-variable
                    # Some devices (ex windows' root hubs) tell they have
                    # one configuration, but they have no configuration
                    # descriptor.
                    continue
                mayRaiseUSBError(result)
                append(config.contents)
        self.__bus_number = libusb1.libusb_get_bus_number(device_p)
        self.__port_number = libusb1.libusb_get_port_number(device_p)
        self.__device_address = libusb1.libusb_get_device_address(device_p)
        if handle_p is not None:
            self.__device_handle = USBDeviceHandle(
                context=context,
                handle=handle_p,
                device=self,
                getFinalizer=self._getFinalizer,
                can_close_device=True,
            )

    @staticmethod
    def close( # pylint: disable=method-hidden
        device_p,
        finalizer_dict,
        descriptor_list,
        libusb_unref_device,
        libusb_free_config_descriptor,

        byref_=byref,
    ):
        while finalizer_dict:
            for handle, finalizer in list(finalizer_dict.items()):
                finalizer()
                assert handle not in finalizer_dict
        if device_p is not None:
            libusb_unref_device(device_p)
        while descriptor_list:
            libusb_free_config_descriptor(
                byref_(descriptor_list.pop()),
            )

    def __str__(self):
        return (
            f'Bus {self.getBusNumber():03} '
            f'Device {self.getDeviceAddress():03}: '
            f'ID {self.getVendorID():04x}:{self.getProductID():04x}'
        )

    def __len__(self):
        return len(self.__configuration_descriptor_list)

    def __getitem__(self, index):
        return USBConfiguration(
            self.__context, self.__configuration_descriptor_list[index], self.getDeviceSpeed())

    def __key(self):
        return (
            id(self.__context), self.__bus_number,
            self.__device_address, self.device_descriptor.idVendor,
            self.device_descriptor.idProduct,
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        # pylint: disable=unidiomatic-typecheck
        return type(self) == type(other) and (
            # pylint: enable=unidiomatic-typecheck
            self.device_p == other.device_p or
            # pylint: disable=protected-access
            self.__key() == other.__key()
            # pylint: enable=protected-access
        )

    def iterConfigurations(self):
        context = self.__context
        for config in self.__configuration_descriptor_list:
            yield USBConfiguration(context, config, self.getDeviceSpeed())

    # BBB
    iterConfiguations = iterConfigurations

    def iterSettings(self):
        for config in self.iterConfigurations():
            for interface in config:
                yield from interface

    def getBusNumber(self):
        """
        Get device's bus number.
        """
        return self.__bus_number

    def getPortNumber(self):
        """
        Get device's port number.
        """
        return self.__port_number

    def getPortNumberList(self):
        """
        Get the port number of each hub toward device.
        """
        port_list = (c_uint8 * PATH_MAX_DEPTH)()
        result = libusb1.libusb_get_port_numbers(
            self.device_p, port_list, len(port_list))
        mayRaiseUSBError(result)
        return list(port_list[:result])

    # TODO: wrap libusb_get_parent when/if libusb removes the need to be inside
    # a libusb_(get|free)_device_list block.

    def getDeviceAddress(self):
        """
        Get device's address on its bus.
        """
        return self.__device_address

    def getbcdUSB(self):
        """
        Get the USB spec version device complies to, in BCD format.
        """
        return self.device_descriptor.bcdUSB

    def getDeviceClass(self):
        """
        Get device's class id.
        """
        return self.device_descriptor.bDeviceClass

    def getDeviceSubClass(self):
        """
        Get device's subclass id.
        """
        return self.device_descriptor.bDeviceSubClass

    def getDeviceProtocol(self):
        """
        Get device's protocol id.
        """
        return self.device_descriptor.bDeviceProtocol

    def getMaxPacketSize0(self):
        """
        Get device's max packet size for endpoint 0 (control).
        """
        return self.device_descriptor.bMaxPacketSize0

    def getMaxPacketSize(self, endpoint):
        """
        Get device's max packet size for given endpoint.

        Warning: this function will not always give you the expected result.
        See https://libusb.org/ticket/77 . You should instead consult the
        endpoint descriptor of current configuration and alternate setting.
        """
        result = libusb1.libusb_get_max_packet_size(self.device_p, endpoint)
        mayRaiseUSBError(result)
        return result

    def getMaxISOPacketSize(self, endpoint):
        """
        Get the maximum size for a single isochronous packet for given
        endpoint.

        Warning: this function will not always give you the expected result.
        See https://libusb.org/ticket/77 . You should instead consult the
        endpoint descriptor of current configuration and alternate setting.
        """
        result = libusb1.libusb_get_max_iso_packet_size(self.device_p, endpoint)
        mayRaiseUSBError(result)
        return result

    def getVendorID(self):
        """
        Get device's vendor id.
        """
        return self.device_descriptor.idVendor

    def getProductID(self):
        """
        Get device's product id.
        """
        return self.device_descriptor.idProduct

    def getbcdDevice(self):
        """
        Get device's release number.
        """
        return self.device_descriptor.bcdDevice

    def getSupportedLanguageList(self):
        """
        Get the list of language ids device has string descriptors for.
        Note: opens the device temporarily and uses synchronous API.
        """
        return self.open().getSupportedLanguageList()

    def getManufacturer(self):
        """
        Get device's manufaturer name.

        Shortcut for .open().getManufacturer() .
        """
        return self.open().getManufacturer()

    def getManufacturerDescriptor(self):
        """
        Get the string index of device's manufacturer.
        You can pass this value to USBHandle.getASCIIStringDescriptor to get
        the actual manufacturer string.
        """
        return self.device_descriptor.iManufacturer

    def getProduct(self):
        """
        Get device's product name.

        Shortcut for .open().getProduct() .
        """
        return self.open().getProduct()

    def getProductDescriptor(self):
        """
        Get the string index of device's product name.
        You can pass this value to USBHandle.getASCIIStringDescriptor to get
        the actual product name string.
        """
        return self.device_descriptor.iProduct

    def getSerialNumber(self):
        """
        Get device's serial number.

        Shortcut for .open().getSerialNumber() .
        """
        return self.open().getSerialNumber()

    def getSerialNumberDescriptor(self):
        """
        Get the string index of device's serial number.
        You can pass this value to USBHandle.getASCIIStringDescriptor to get
        the actual serial number string.
        """
        return self.device_descriptor.iSerialNumber

    def getNumConfigurations(self):
        """
        Get device's number of possible configurations.
        """
        return self.device_descriptor.bNumConfigurations

    def getDeviceSpeed(self):
        """
        Get device's speed.

        Returns one of:
            SPEED_UNKNOWN
            SPEED_LOW
            SPEED_FULL
            SPEED_HIGH
            SPEED_SUPER
            SPEED_SUPER_PLUS
        """
        return libusb1.libusb_get_device_speed(self.device_p)

    def open(self):
        """
        Open device.
        Returns an USBDeviceHandle instance.
        """
        if self.__device_handle is not None:
            return self.__device_handle
        handle = libusb1.libusb_device_handle_p()
        mayRaiseUSBError(libusb1.libusb_open(self.device_p, byref(handle)))
        return USBDeviceHandle(
            context=self.__context,
            handle=handle,
            device=self,
            getFinalizer=self._getFinalizer,
            can_close_device=False,
        )

_zero_tv = libusb1.timeval(0, 0)
_zero_tv_p = byref(_zero_tv)
_null_pointer = c_void_p()
_NULL_LOG_CALLBACK = libusb1.libusb_log_cb_p(0)

class USBContext(_LibUSB1Finalizer):
    """
    libusb1 USB context.

    Provides methods to enumerate & look up USB devices.
    Also provides access to global (device-independent) libusb1 functions.
    """
    __context_p = None
    __added_cb = None
    __removed_cb = None
    __poll_cb_user_data = None
    __auto_open = True
    __has_pollfd_finalizer = False
    __mayRaiseUSBError = staticmethod(mayRaiseUSBError)
    __libusb_handle_events = None

    # pylint: disable=no-self-argument,protected-access
    def _validContext(func):
        # Defined inside USBContext so we can access "self.__*".
        @contextlib.contextmanager
        def refcount(self):
            with self.__context_cond:
                if not self.__context_p and self.__auto_open:
                    # BBB
                    warnings.warn(
                        'Use "with USBContext() as context:" for safer cleanup'
                        ' on interpreter shutdown. See also USBContext.open().',
                        DeprecationWarning,
                        stacklevel=4
                    )
                    self.open()
                self.__context_refcount += 1
            try:
                yield
            finally:
                with self.__context_cond:
                    self.__context_refcount -= 1
                    if not self.__context_refcount:
                        self.__context_cond.notify_all()
        if inspect.isgeneratorfunction(func):
            def wrapper(self, *args, **kw):
                with refcount(self):
                    if self.__context_p:
                        # pylint: disable=not-callable
                        generator = func(self, *args, **kw)
                        # pylint: enable=not-callable
                        try:
                            yield from generator
                        finally:
                            generator.close()
        else:
            def wrapper(self, *args, **kw):
                with refcount(self):
                    if self.__context_p:
                        # pylint: disable=not-callable
                        return func(self, *args, **kw)
                        # pylint: enable=not-callable
                    return None
        functools.update_wrapper(wrapper, func)
        return wrapper
    # pylint: enable=no-self-argument,protected-access

    def __init__(
        self,
        log_level=None,
        use_usbdk=False,
        with_device_discovery=True,
        log_callback=None,
    ):
        """
        Create a new USB context.

        log_level (LOG_LEVEL_*)
            Sets the context's log level as soon as it is created.
            Maybe have no effect depending on libusb's build options.
        use_usbdk (bool)
            Windows only.
            Whether to use the UsbDk backend if available.
        with_device_discovery (bool)
            Linux only.
            Disables device scan while initialising the library.
            This has knowck-on effects on how devices may be opened and how
            descriptors are accessed. For more details, see libusb1's
            documentation.
        log_callback ((int, bytes): None)
            Context's log callback function.

        Note: providing non-default values may cause context creation (during
        __enter__, open, or the first context-dependent call, whichever happens
        first) to fail if libusb is older than v1.0.27 .
        """
        super().__init__()
        # Used to prevent an exit to cause a segfault if a concurrent thread
        # is still in libusb.
        self.__context_refcount = 0
        self.__context_cond = threading.Condition()
        self.__context_p = libusb1.libusb_context_p()
        assert not self.__context_p
        self.__hotplug_callback_dict = {}
        self.__log_level = log_level
        self.__use_usbdk = use_usbdk
        self.__with_device_discovery = with_device_discovery
        self.__user_log_callback = log_callback
        self.__log_callback_p = libusb1.libusb_log_cb_p(self.__log_callback)

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        """
        Finish context initialisation, as is normally done in __enter__ .

        This happens automatically on the first method call needing access to
        the uninitialised properties, but with a warning.
        Call this method ONLY if your usage pattern prevents you from using the
            with USBContext() as context:
        form: this means there are ways to avoid calling close(), which can
        cause issues particularly hard to debug (ex: interpreter hangs on
        exit).

        Calls loadLibrary.
        """
        assert self.__context_refcount == 0
        assert not self.__context_p
        loadLibrary()
        self.__libusb_handle_events = libusb1.libusb_handle_events
        option_array = (
            libusb1.libusb_init_option * libusb1.LIBUSB_OPTION_MAX
        )()
        option_count = 0
        if self.__log_level is not None:
            option = option_array[option_count]
            option_count += 1
            option.option = libusb1.LIBUSB_OPTION_LOG_LEVEL
            option.value.ival = self.__log_level
        if self.__use_usbdk:
            option = option_array[option_count]
            option_count += 1
            option.option = libusb1.LIBUSB_OPTION_USE_USBDK
            option.value.ival = 1
        if not self.__with_device_discovery:
            option = option_array[option_count]
            option_count += 1
            option.option = libusb1.LIBUSB_OPTION_NO_DEVICE_DISCOVERY
            option.value.ival = 1
        if self.__user_log_callback is not None:
            option = option_array[option_count]
            option_count += 1
            option.option = libusb1.LIBUSB_OPTION_LOG_CB
            option.value.log_cbval = self.__log_callback_p
        mayRaiseUSBError(libusb1.libusb_init_context(
            byref(self.__context_p),
            option_array,
            option_count,
        ))
        self.__close = weakref.finalize(
            self,
            self.___close, # Note: static method
            context_p=self.__context_p,
            hotplug_callback_dict=self.__hotplug_callback_dict,
            finalizer_dict=self._finalizer_dict,
            libusb_exit=libusb1.libusb_exit,
            libusb_hotplug_deregister_callback=libusb1.libusb_hotplug_deregister_callback,
        )
        return self

    def close(self):
        """
        Close (destroy) this USB context, and all related instances.

        When this method has been called, methods on its instance will
        become mosty no-ops, returning None until explicitly re-opened
        (by calling open() or __enter__()).

        Note: "exit" is a deprecated alias of "close".
        """
        self.__auto_open = False
        self.__context_cond.acquire()
        try:
            while self.__context_refcount and self.__context_p:
                self.__context_cond.wait()
            self.__close()
            # pylint: disable=unused-private-member
            self.__added_cb = None
            self.__removed_cb = None
            self.__poll_cb_user_data = None
            # pylint: enable=unused-private-member
        finally:
            self.__context_cond.notify_all()
            self.__context_cond.release()

    # BBB
    exit = close

    @staticmethod
    def __close(): # pylint: disable=method-hidden
        # Placeholder, masked on open()
        pass

    @staticmethod
    def ___close( # pylint: disable=method-hidden
        context_p,
        hotplug_callback_dict,
        finalizer_dict,
        libusb_exit,
        libusb_hotplug_deregister_callback,
    ):
        while hotplug_callback_dict:
            # Duplicates hotplugDeregisterCallback logic, to avoid finalizer
            # referencing its own instance.
            handle, _ = hotplug_callback_dict.popitem()
            libusb_hotplug_deregister_callback(context_p, handle)
        while finalizer_dict:
            for handle, finalizer in list(finalizer_dict.items()):
                finalizer()
                assert handle not in finalizer_dict
        libusb_exit(context_p)
        context_p.value = None

    @_validContext
    def getDeviceIterator(self, skip_on_error=False):
        """
        Return an iterator over all USB devices currently plugged in, as USBDevice
        instances.

        skip_on_error (bool)
            If True, ignore devices which raise USBError.
        """
        libusb_free_device_list = libusb1.libusb_free_device_list
        device_p_p = libusb1.libusb_device_p_p()
        device_list_len = libusb1.libusb_get_device_list(self.__context_p,
                                                         byref(device_p_p))
        mayRaiseUSBError(device_list_len)
        try:
            for device_p in device_p_p[:device_list_len]:
                try:
                    device = USBDevice(
                        context=self,
                        device_p=device_p,
                        getFinalizer=self._getFinalizer,
                        can_load_configuration=True,
                        can_change_refcount=True,
                        handle_p=None,
                    )
                except USBError:
                    if not skip_on_error:
                        raise
                else:
                    yield device
        finally:
            libusb_free_device_list(device_p_p, 1)

    def getDeviceList(self, skip_on_access_error=False, skip_on_error=False):
        """
        Return a list of all USB devices currently plugged in, as USBDevice
        instances.

        skip_on_error (bool)
            If True, ignore devices which raise USBError.

        skip_on_access_error (bool)
            DEPRECATED. Alias for skip_on_error.
        """
        return list(
            self.getDeviceIterator(
                skip_on_error=skip_on_access_error or skip_on_error,
            ),
        )

    def getByVendorIDAndProductID(
            self, vendor_id, product_id,
            skip_on_access_error=False, skip_on_error=False):
        """
        Get the first USB device matching given vendor and product ids.
        Returns an USBDevice instance, or None if no present device match.
        skip_on_error (bool)
            (see getDeviceList)
        skip_on_access_error (bool)
            (see getDeviceList)
        """
        device_iterator = self.getDeviceIterator(
            skip_on_error=skip_on_access_error or skip_on_error,
        )
        try:
            for device in device_iterator:
                if device.getVendorID() == vendor_id and \
                        device.getProductID() == product_id:
                    return device
                device.close()
        finally:
            device_iterator.close()
        return None

    def openByVendorIDAndProductID(
            self, vendor_id, product_id,
            skip_on_access_error=False, skip_on_error=False):
        """
        Get the first USB device matching given vendor and product ids.
        Returns an USBDeviceHandle instance, or None if no present device
        match.
        skip_on_error (bool)
            (see getDeviceList)
        skip_on_access_error (bool)
            (see getDeviceList)
        """
        result = self.getByVendorIDAndProductID(
            vendor_id, product_id,
            skip_on_access_error=skip_on_access_error,
            skip_on_error=skip_on_error)
        if result is not None:
            return result.open()
        return None

    @_validContext
    def wrapSysDevice(self, sys_device):
        """
        Wrap sys_device to obtain a USBDeviceHandle instance.

        sys_device (file, int):
            File or file descriptor of the sys device node to wrap.
            You must keep this file open while the device is,
            and are expected to close it any time after it is closed.

        You may get a USBDevice instance by calling getDevice on the returned
        value, but note that this device will be closed once the handle is.
        """
        if not isinstance(sys_device, int):
            sys_device = sys_device.fileno()
        handle_p = libusb1.libusb_device_handle_p()
        mayRaiseUSBError(
            libusb1.libusb_wrap_sys_device(
                self.__context_p,
                sys_device,
                byref(handle_p),
            )
        )
        return USBDevice(
            context=self,
            device_p=libusb1.libusb_get_device(handle_p),
            getFinalizer=self._getFinalizer,
            can_load_configuration=True, # XXX: give the caller control ?
            can_change_refcount=False,
            handle_p=handle_p,
        ).open()

    @_validContext
    def getPollFDList(self):
        """
        Return file descriptors to be used to poll USB events.
        You should not have to call this method, unless you are integrating
        this class with a polling mechanism.
        """
        pollfd_p_p = libusb1.libusb_get_pollfds(self.__context_p)
        if not pollfd_p_p:
            errno = get_errno()
            if errno:
                raise OSError(errno)
            # Assume not implemented
            raise NotImplementedError(
                'Your libusb does not seem to implement pollable FDs')
        try:
            result = []
            append = result.append
            fd_index = 0
            while pollfd_p_p[fd_index]:
                append((
                    pollfd_p_p[fd_index].contents.fd,
                    pollfd_p_p[fd_index].contents.events,
                ))
                fd_index += 1
        finally:
            libusb1.libusb_free_pollfds(pollfd_p_p)
        return result

    @_validContext
    def handleEvents(self):
        """
        Handle any pending event (blocking).
        See libusb1 documentation for details (there is a timeout, so it's
        not "really" blocking).
        """
        self.__mayRaiseUSBError(
            self.__libusb_handle_events(self.__context_p),
        )

    # TODO: handleEventsCompleted

    @_validContext
    def handleEventsTimeout(self, tv=0):
        """
        Handle any pending event.
        If tv is 0, will return immediately after handling already-pending
        events.
        Otherwise, defines the maximum amount of time to wait for events, in
        seconds.
        """
        if tv is None:
            tv = 0
        tv_s = int(tv)
        real_tv = libusb1.timeval(tv_s, int((tv - tv_s) * 1000000))
        mayRaiseUSBError(
            libusb1.libusb_handle_events_timeout(
                self.__context_p, byref(real_tv),
            ),
        )

    # TODO: handleEventsTimeoutCompleted

    @_validContext
    def interruptEventHandler(self):
        """
        Interrupt any active thread that is handling events.
        This is mainly useful for interrupting a dedicated event handling thread
        when the application wishes to exit.
        """
        libusb1.libusb_interrupt_event_handler(self.__context_p)

    @_validContext
    def setPollFDNotifiers(
            self, added_cb=None, removed_cb=None, user_data=None):
        """
        Give libusb1 methods to call when it should add/remove file descriptor
        for polling.
        You should not have to call this method, unless you are integrating
        this class with a polling mechanism.
        """
        if added_cb is None:
            added_cb = _null_pointer
        else:
            added_cb = libusb1.libusb_pollfd_added_cb_p(added_cb)
        if removed_cb is None:
            removed_cb = _null_pointer
        else:
            removed_cb = libusb1.libusb_pollfd_removed_cb_p(removed_cb)
        if user_data is None:
            user_data = _null_pointer
        # pylint: disable=unused-private-member
        self.__added_cb = added_cb
        self.__removed_cb = removed_cb
        self.__poll_cb_user_data = user_data
        # pylint: enable=unused-private-member
        libusb1.libusb_set_pollfd_notifiers(
            self.__context_p,
            cast(added_cb, libusb1.libusb_pollfd_added_cb_p),
            cast(removed_cb, libusb1.libusb_pollfd_removed_cb_p),
            user_data,
        )
        if not self.__has_pollfd_finalizer:
            # Note: the above condition is just to avoid creating finalizers on
            # every call. If more than one is created (because of a
            # race-condition) it is not a big deal, as __finalizePollFDNotifiers
            # will do the right thing even if called multiple times in a row.
            self.__has_pollfd_finalizer = True
            self.getFinalizer(
                self,
                self.__finalizePollFDNotifiers, # Note: staticmethod
                context_p=self.__context_p,
                libusb_set_pollfd_notifiers=libusb1.libusb_set_pollfd_notifiers,
            )

    @staticmethod
    def __finalizePollFDNotifiers(
        context_p,
        libusb_set_pollfd_notifiers,

        null_pointer=_null_pointer,
        added_cb_p=cast(_null_pointer, libusb1.libusb_pollfd_added_cb_p),
        removed_cb_p=cast(_null_pointer, libusb1.libusb_pollfd_removed_cb_p),
    ):
        libusb_set_pollfd_notifiers(
            context_p,
            added_cb_p,
            removed_cb_p,
            null_pointer,
        )

    @_validContext
    def getNextTimeout(self):
        """
        Returns the next internal timeout that libusb needs to handle, in
        seconds, or None if no timeout is needed.
        You should not have to call this method, unless you are integrating
        this class with a polling mechanism.
        """
        timeval = libusb1.timeval()
        result = libusb1.libusb_get_next_timeout(
            self.__context_p, byref(timeval))
        if result == 0:
            return None
        if result == 1:
            return timeval.tv_sec + (timeval.tv_usec * 0.000001)
        raiseUSBError(result)
        return None # unreachable, to make pylint happy

    @_validContext
    def setDebug(self, level):
        """
        Set debugging level. See LOG_LEVEL_* constants.
        Note: depending on libusb compilation settings, this might have no
        effect.
        """
        libusb1.libusb_set_debug(self.__context_p, level)

    @_validContext
    def tryLockEvents(self):
        warnings.warn(
            'You may not be able to unlock in the event of USBContext exit. '
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        return libusb1.libusb_try_lock_events(self.__context_p)

    @_validContext
    def lockEvents(self):
        warnings.warn(
            'You may not be able to unlock in the event of USBContext exit. '
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        libusb1.libusb_lock_events(self.__context_p)

    @_validContext
    def lockEventWaiters(self):
        warnings.warn(
            'You may not be able to unlock in the event of USBContext exit. '
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        libusb1.libusb_lock_event_waiters(self.__context_p)

    @_validContext
    def waitForEvent(self, tv=0):
        warnings.warn(
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        if tv is None:
            tv = 0
        tv_s = int(tv)
        real_tv = libusb1.timeval(tv_s, int((tv - tv_s) * 1000000))
        libusb1.libusb_wait_for_event(self.__context_p, byref(real_tv))

    @_validContext
    def unlockEventWaiters(self):
        warnings.warn(
            'This method will lock in the event of USBContext exit, '
            'preventing libusb lock release. '
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        libusb1.libusb_unlock_event_waiters(self.__context_p)

    @_validContext
    def eventHandlingOK(self):
        warnings.warn(
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        return libusb1.libusb_event_handling_ok(self.__context_p)

    @_validContext
    def unlockEvents(self):
        warnings.warn(
            'This method will lock in the event of USBContext exit, '
            'preventing libusb lock release. '
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        libusb1.libusb_unlock_events(self.__context_p)

    @_validContext
    def handleEventsLocked(self):
        warnings.warn(
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        # XXX: does tv parameter need to be exposed ?
        mayRaiseUSBError(libusb1.libusb_handle_events_locked(
            self.__context_p, _zero_tv_p,
        ))

    @_validContext
    def eventHandlerActive(self):
        warnings.warn(
            'Consider looping over handleEvents() in a thread.',
            DeprecationWarning,
        )
        return libusb1.libusb_event_handler_active(self.__context_p)

    @staticmethod
    def hasCapability(capability):
        """
        Backward-compatibility alias for module-level hasCapability.
        """
        return hasCapability(capability)

    @_validContext
    def hotplugRegisterCallback(
            self, callback,
            # pylint: disable=undefined-variable
            events=HOTPLUG_EVENT_DEVICE_ARRIVED | HOTPLUG_EVENT_DEVICE_LEFT,
            flags=HOTPLUG_ENUMERATE,
            vendor_id=HOTPLUG_MATCH_ANY,
            product_id=HOTPLUG_MATCH_ANY,
            dev_class=HOTPLUG_MATCH_ANY,
            # pylint: enable=undefined-variable
        ):
        """
        Registers an hotplug callback.
        On success, returns an opaque value which can be passed to
        hotplugDeregisterCallback.
        Callback must accept the following positional arguments:
        - this USBContext instance
        - an USBDevice instance
          If device has left, configuration descriptors may not be
          available. Its device descriptor will be available.
        - event type, one of:
            HOTPLUG_EVENT_DEVICE_ARRIVED
            HOTPLUG_EVENT_DEVICE_LEFT
        Callback must return whether it must be unregistered (any true value
        to be unregistered, any false value to be kept registered).

        Note: given callback will be invoked during event handling, meaning
        it cannot call any synchronous libusb function.
        """
        def wrapped_callback(context_p, device_p, event, _):
            assert context_p == self.__context_p.value, (
                context_p, self.__context_p,
            )
            device = USBDevice(
                context=self,
                device_p=device_p,
                getFinalizer=self._getFinalizer,
                # pylint: disable=undefined-variable
                can_load_configuration=event != HOTPLUG_EVENT_DEVICE_LEFT,
                # pylint: enable=undefined-variable
                can_change_refcount=True,
                handle_p=None,
            )
            unregister = bool(callback(
                self,
                device,
                event,
            ))
            if unregister:
                del self.__hotplug_callback_dict[handle]
            return unregister
        handle = c_int()
        callback_p = libusb1.libusb_hotplug_callback_fn_p(wrapped_callback)
        mayRaiseUSBError(libusb1.libusb_hotplug_register_callback(
            self.__context_p, events, flags, vendor_id, product_id, dev_class,
            callback_p, None, byref(handle),
        ))
        handle = handle.value
        # Keep strong references
        assert handle not in self.__hotplug_callback_dict, (
            handle,
            self.__hotplug_callback_dict,
        )
        self.__hotplug_callback_dict[handle] = (callback_p, wrapped_callback)
        return handle

    @_validContext
    def hotplugDeregisterCallback(self, handle):
        """
        Deregisters an hotplug callback.
        handle (opaque)
            Return value of a former hotplugRegisterCallback call.
        """
        del self.__hotplug_callback_dict[handle]
        libusb1.libusb_hotplug_deregister_callback(self.__context_p, handle)

    def __log_callback(self, _unused_context_p, level, value):
        """
        Internal log callback function, calls into the user-provided function
        if any.
        """
        # Note: as of libusb1, context_p is de facto guaranteed to be us:
        #  ctx->log_handler(ctx, level, buf);
        # so do not bother checking.
        user_log_callback = self.__user_log_callback
        if user_log_callback is not None:
            user_log_callback(self, level, value)

    @_validContext
    def setLogCallback(self, log_callback):
        """
        Change the active log callback for this context.

        log_callback (None, (USBContext, int, bytes): None)
            The function called when libusb emits log messages for the current
            context.
            None to disable the callback.
        """
        user_log_callback_was_unset = self.__user_log_callback is None
        self.__user_log_callback = log_callback
        if user_log_callback_was_unset != (log_callback is None):
            libusb1.libusb_set_log_cb(
                self.__context_p,
                (
                    _NULL_LOG_CALLBACK
                    if log_callback is None else
                    self.__log_callback_p
                ),
                libusb1.LIBUSB_LOG_CB_CONTEXT,
            )

del USBContext._validContext

def getVersion():
    """
    Returns underlying libusb's version information as a 6-namedtuple (or
    6-tuple if namedtuples are not avaiable):
    - major
    - minor
    - micro
    - nano
    - rc
    - describe
    Returns (0, 0, 0, 0, '', '') if libusb doesn't have required entry point.

    Calls loadLibrary.
    """
    loadLibrary()
    version = libusb1.libusb_get_version().contents
    return Version(
        version.major,
        version.minor,
        version.micro,
        version.nano,
        version.rc,
        version.describe,
    )

def hasCapability(capability):
    """
    Tests feature presence.

    capability should be one of:
        CAP_HAS_CAPABILITY
        CAP_HAS_HOTPLUG
        CAP_HAS_HID_ACCESS
        CAP_SUPPORTS_DETACH_KERNEL_DRIVER

    Calls loadLibrary.
    """
    loadLibrary()
    return libusb1.libusb_has_capability(capability)

class __GlobalLogCallback: # pylint: disable=too-few-public-methods
    """
    Singleton class keeping a reference to the global log callback function
    so it is unregistered from libusb before the module gets garbage-collected.
    """
    __user_log_callback = None
    __finalizer = None

    def __init__(self):
        self.__log_callback_p = libusb1.libusb_log_cb_p(self.__log_callback)

    @staticmethod
    def __close(
        libusb_set_log_cb,
        LIBUSB_LOG_CB_GLOBAL,
    ):
        libusb_set_log_cb(None, _NULL_LOG_CALLBACK, LIBUSB_LOG_CB_GLOBAL)

    def __log_callback(self, context_p, level, message):
        # As of at least libusb1, context_p of the global log callback
        # is always NULL, even when the event originated from a context.
        # So just ignore it here, forcing it to None.
        # Should it change later, then some USBContext lookup will be
        # needed.
        _ = context_p
        user_log_callback = self.__user_log_callback
        if user_log_callback is not None:
            user_log_callback(None, level, message)

    def __call__(self, log_callback):
        """
        Set the global log callback.

        log_callback (None, (None, int, bytes): None)
            A callable to set as libusb global log callback, or None to disable
            this feature.
            The first argument should be ignored.
            The second argument is the message level.
            The third argument is the message itself, as bytes.

        Calls loadLibrary.
        libusb_set_log_cb will be called once more during module teardown.
        """
        if self.__finalizer is None:
            # Lazy initialisation, so loadLibrary is not called at
            # module load time.
            loadLibrary()
            self.__finalizer = weakref.finalize(
                self,
                self.__close, # Note: static method
                libusb_set_log_cb=libusb1.libusb_set_log_cb,
                LIBUSB_LOG_CB_GLOBAL=libusb1.LIBUSB_LOG_CB_GLOBAL,
            )
        user_log_callback_was_unset = self.__user_log_callback is None
        self.__user_log_callback = log_callback
        if user_log_callback_was_unset != (log_callback is None):
            libusb1.libusb_set_log_cb(
                None,
                (
                    _NULL_LOG_CALLBACK
                    if log_callback is None else
                    self.__log_callback_p
                ),
                libusb1.LIBUSB_LOG_CB_GLOBAL,
            )
setLogCallback = __GlobalLogCallback().__call__

def setLocale(locale):
    """
    Set locale used for translatable libusb1 messages.

    locale (str)
        2 letter ISO 639-1 code, optionally followed by region and codeset.

    Calls loadLibrary.
    """
    loadLibrary()
    mayRaiseUSBError(
        libusb1.libusb_setlocale(locale.encode('ascii'))
    )

class LibUSBContext(USBContext):
    """
    Backward-compatibility alias for USBContext.
    """
    def __init__(self):
        warnings.warn(
            'LibUSBContext is being renamed to USBContext',
            DeprecationWarning,
        )
        super().__init__()

loadLibrary = libusb1.loadLibrary
