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

# pylint: disable=invalid-name, missing-docstring, too-many-public-methods

from ctypes import pointer, sizeof
import functools
import gc
import itertools
import sys
import unittest
import weakref
import usb1
from . import libusb1

buff_len = 1024
buffer_base = [x % 256 for x in range(buff_len)]
buff = bytes(buffer_base)
other_buff = bytes(reversed(buffer_base))
bytearray_buff = bytearray(buffer_base)

class USBContext(usb1.USBContext):
    def open(self):
        try:
            return super().open()
        except usb1.USBError:
            raise unittest.SkipTest(
                'usb1.USBContext() fails - no USB bus on system ?'
            )

def checkTransferAllocCount(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kw):
        before = self.transfer_alloc_count
        libusb_free_transfer = libusb1.libusb_free_transfer
        libusb_alloc_transfer = libusb1.libusb_alloc_transfer
        try:
            libusb1.libusb_free_transfer = self._fakeFreeTransfer
            libusb1.libusb_alloc_transfer = self._fakeAllocTransfer
            result = func(self, *args, **kw)
        finally:
            libusb1.libusb_free_transfer = libusb_free_transfer
            libusb1.libusb_alloc_transfer = libusb_alloc_transfer
        gc.collect()
        self.assertEqual(self.transfer_alloc_count, before)
        return result
    return wrapper

class USBTransferTests(unittest.TestCase):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        usb1.loadLibrary()
        self.transfer_alloc_count = 0

    def _fakeFreeTransfer(self, _):
        self.transfer_alloc_count -= 1

    def _fakeAllocTransfer(self, isochronous_count):
        self.transfer_alloc_count += 1
        buffer = bytearray(
            sizeof(
                libusb1.libusb_transfer,
            ) + sizeof(
                libusb1.libusb_iso_packet_descriptor,
            ) * max(0, isochronous_count - 1),
        )
        transfer = libusb1.libusb_transfer.from_buffer(buffer)
        # Keep a reference (in the finalizer itself) to the buffer for as long
        # as transfer is alive.
        weakref.finalize(transfer, lambda _: None, buffer)
        return pointer(transfer)

    @staticmethod
    def getTransfer(iso_packets=0):
        # Dummy handle
        return usb1.USBTransfer(
            context=None,
            handle=None,
            iso_packets=iso_packets,
            before_submit=lambda x: None,
            after_completion=lambda x: None,
            registerFinalizer=lambda handle, finalizer: None,
            unregisterFinalizer=lambda handle: None,
        )

    @staticmethod
    def testGetVersion():
        """
        Just testing getVersion doesn't raise...
        """
        usb1.getVersion()

    @staticmethod
    def testHasCapability():
        """
        Just testing hasCapability doesn't raise...
        """
        usb1.hasCapability(usb1.CAP_HAS_CAPABILITY)

    @checkTransferAllocCount
    def testSetControl(self):
        """
        Simplest test: feed some data, must not raise.
        """
        transfer = self.getTransfer()
        request_type = usb1.TYPE_STANDARD
        request = usb1.REQUEST_GET_STATUS
        value = 0
        index = 0
        def callback(transfer):
            pass
        user_data = []
        timeout = 1000

        # All provided, buffer variant
        transfer.setControl(
            request_type, request, value, index, buff,
            callback=callback, user_data=user_data, timeout=timeout)
        self.assertEqual(buff, transfer.getBuffer())
        self.assertRaises(ValueError, transfer.setBuffer, buff)
        # All provided, buffer length variant
        transfer.setControl(
            request_type, request, value, index, buff_len,
            callback=callback, user_data=user_data, timeout=timeout)
        # No timeout
        transfer.setControl(
            request_type, request, value, index, buff,
            callback=callback, user_data=user_data)
        # No user data
        transfer.setControl(
            request_type, request, value, index, buff, callback=callback)
        # No callback
        transfer.setControl(request_type, request, value, index, buff)

    def _testTransferSetter(self, transfer, setter_id):
        endpoint = 0x81
        def callback(transfer):
            pass
        user_data = []
        timeout = 1000
        setter = getattr(transfer, setter_id)
        # All provided, buffer variant
        setter(
            endpoint, buff, callback=callback, user_data=user_data,
            timeout=timeout)
        self.assertEqual(buff, transfer.getBuffer())
        transfer.setBuffer(other_buff)
        self.assertEqual(other_buff, transfer.getBuffer())
        transfer.setBuffer(bytearray_buff)
        self.assertEqual(bytearray_buff, transfer.getBuffer())
        transfer.setBuffer(buff_len)
        self.assertEqual(buff_len, len(transfer.getBuffer()))
        # All provided, buffer length variant
        setter(
            endpoint, buff_len, callback=callback, user_data=user_data,
            timeout=timeout)
        # No timeout
        setter(endpoint, buff, callback=callback, user_data=user_data)
        # No user data
        setter(endpoint, buff, callback=callback)
        # No callback
        setter(endpoint, buff)

    @checkTransferAllocCount
    def testSetBulk(self):
        """
        Simplest test: feed some data, must not raise.
        Also, test setBuffer/getBuffer.
        """
        self._testTransferSetter(self.getTransfer(), 'setBulk')

    @checkTransferAllocCount
    def testSetInterrupt(self):
        """
        Simplest test: feed some data, must not raise.
        Also, test setBuffer/getBuffer.
        """
        self._testTransferSetter(self.getTransfer(), 'setInterrupt')

    @checkTransferAllocCount
    def testSetIsochronous(self):
        """
        Simplest test: feed some data, must not raise.
        Also, test setBuffer/getBuffer/getISOBufferList/iterISO.
        """
        iso_transfer_count = 16
        transfer = self.getTransfer(iso_transfer_count)
        self._testTransferSetter(transfer, 'setIsochronous')
        # Returns whole buffers
        self.assertEqual(
            bytearray(itertools.chain(*transfer.getISOBufferList())),
            buff,
        )
        # Returns actually transfered data, so here nothing
        self.assertEqual(bytearray(
            itertools.chain(*[x for _, x in transfer.iterISO()])),
            bytearray(),
        )
        # Fake reception of whole transfers
        c_transfer = getattr(
          transfer,
          '_' + transfer.__class__.__name__ + '__transfer'
        )
        for iso_metadata in libusb1.get_iso_packet_list(c_transfer):
            iso_metadata.actual_length = iso_metadata.length
        # Now iterISO returns everythig
        self.assertEqual(bytearray(
            itertools.chain(*[x for _, x in transfer.iterISO()])),
            buff,
        )

    @checkTransferAllocCount
    def testSetGetCallback(self):
        transfer = self.getTransfer()
        def callback(transfer):
            pass
        transfer.setCallback(callback)
        got_callback = transfer.getCallback()
        self.assertEqual(callback, got_callback)

    def _testDescriptors(self, get_extra=False):
        """
        Test descriptor walk.
        Needs any usb device, which won't be opened.
        """
        with USBContext() as context:
            device_list = context.getDeviceList(skip_on_error=True)
            found = False
            seen_extra = False
            for device in device_list:
                device.getBusNumber()
                device.getPortNumber()
                device.getPortNumberList()
                device.getDeviceAddress()
                for settings in device.iterSettings():
                    for endpoint in settings:
                        pass
                for configuration in device.iterConfigurations():
                    if get_extra and len(configuration.getExtra()) > 0:
                        seen_extra = True
                    for interface in configuration:
                        for settings in interface:
                            if get_extra and len(settings.getExtra()) > 0:
                                seen_extra = True
                            for endpoint in settings:
                                if get_extra and len(endpoint.getExtra()) > 0:
                                    seen_extra = True
                                found = True
            if not found:
                raise unittest.SkipTest('descriptor walk test did not complete')
            if get_extra and not seen_extra:
                raise unittest.SkipTest('did not see any extra descriptors')

    def testDescriptors(self):
        self._testDescriptors()

    def testDescriptorsWithExtra(self):
        self._testDescriptors(get_extra=True)

    def testDefaultEnumScope(self):
        """
        Enum instances must only affect the scope they are created in.
        """
        ENUM_NAME = 'THE_ANSWER'
        ENUM_VALUE = 42
        local_dict = locals()
        global_dict = globals()
        self.assertEqual(local_dict.get(ENUM_NAME), None)
        self.assertEqual(global_dict.get(ENUM_NAME), None)
        self.assertEqual(getattr(libusb1, ENUM_NAME, None), None)
        # pylint: disable=unused-variable
        TEST_ENUM = libusb1.Enum({ENUM_NAME: ENUM_VALUE})
        # pylint: enable=unused-variable
        self.assertEqual(local_dict.get(ENUM_NAME), ENUM_VALUE)
        self.assertEqual(global_dict.get(ENUM_NAME), None)
        self.assertEqual(getattr(libusb1, ENUM_NAME, None), None)

    def testExplicitEnumScope(self):
        """
        Enum instances must only affect the scope they are created in.
        """
        ENUM_NAME = 'THE_ANSWER'
        ENUM_VALUE = 42
        local_dict = locals()
        global_dict = globals()
        self.assertEqual(local_dict.get(ENUM_NAME), None)
        self.assertEqual(global_dict.get(ENUM_NAME), None)
        self.assertEqual(getattr(libusb1, ENUM_NAME, None), None)
        # pylint: disable=unused-variable
        TEST_ENUM = libusb1.Enum({ENUM_NAME: ENUM_VALUE}, global_dict)
        # pylint: enable=unused-variable
        try:
            self.assertEqual(local_dict.get(ENUM_NAME), None)
            self.assertEqual(global_dict.get(ENUM_NAME), ENUM_VALUE)
            self.assertEqual(getattr(libusb1, ENUM_NAME, None), None)
        finally:
            del global_dict[ENUM_NAME]

    def testImplicitUSBContextOpening(self):
        """
        Test pre-1.5 API backward compatibility.
        First method call which needs a context succeeds.
        Further calls return None.
        """
        context = USBContext() # Deprecated
        try:
            fd_list = context.getPollFDList()
        except NotImplementedError:
            raise unittest.SkipTest('libusb without file descriptor events')
        self.assertNotEqual(fd_list, None)
        context.exit() # Deprecated
        self.assertEqual(context.getPollFDList(), None)

    def testHasVersion(self):
        # Property is present and non-empty
        self.assertTrue(usb1.__version__)

if __name__ == '__main__':
    unittest.main()
