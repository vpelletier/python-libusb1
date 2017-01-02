# Copyright (C) 2010-2016  Vincent Pelletier <plr.vincent@gmail.com>
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
import unittest
import sys
import itertools
import select
import threading
import usb1
import libusb1
from ctypes import pointer

buff_len = 1024
buffer_base = [x % 256 for x in range(buff_len)]
if sys.version_info[0] == 3:
    buff = bytes(buffer_base)
    other_buff = bytes(reversed(buffer_base))
else:
    buff = ''.join(chr(x) for x in buffer_base)
    other_buff = ''.join(chr(x) for x in reversed(buffer_base))
bytearray_buff = bytearray(buffer_base)

class USBContext(usb1.USBContext):
    def open(self):
        try:
            return super(USBContext, self).open()
        except usb1.USBError:
            raise unittest.SkipTest(
                'usb1.USBContext() fails - no USB bus on system ?'
            )

class PollDetector(object):
    def __init__(self, *args, **kw):
        try:
            poll = select.poll
        except AttributeError:
            raise unittest.SkipTest('select.poll missing')
        self.__poll = poll(*args, **kw)
        self.__event = threading.Event()

    def poll(self, *args, **kw):
        self.__event.set()
        return self.__poll.poll(*args, **kw)

    def wait(self, *args, **kw):
        self.__event.wait(*args, **kw)

    def __getattr__(self, name):
        return getattr(self.__poll, name)

class USBTransferTests(unittest.TestCase):
    @staticmethod
    def getTransfer(iso_packets=0):
        # Dummy handle
        return usb1.USBTransfer(
            pointer(libusb1.libusb_device_handle()),
            iso_packets, lambda x: None, lambda x: None)

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

    def testSetBulk(self):
        """
        Simplest test: feed some data, must not raise.
        Also, test setBuffer/getBuffer.
        """
        self._testTransferSetter(self.getTransfer(), 'setBulk')

    def testSetInterrupt(self):
        """
        Simplest test: feed some data, must not raise.
        Also, test setBuffer/getBuffer.
        """
        self._testTransferSetter(self.getTransfer(), 'setInterrupt')

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

    def testSetGetCallback(self):
        transfer = self.getTransfer()
        def callback(transfer):
            pass
        transfer.setCallback(callback)
        got_callback = transfer.getCallback()
        self.assertEqual(callback, got_callback)

    def testUSBPollerThreadExit(self):
        """
        USBPollerThread must exit by itself when context is destroyed.
        """
        with USBContext() as context:
            poll_detector = PollDetector()
            try:
                poller = usb1.USBPollerThread(context, poll_detector)
            except OSError:
                raise unittest.SkipTest('libusb without file descriptor events')
            poller.start()
            poll_detector.wait(1)
        poller.join(1)
        self.assertFalse(poller.is_alive())

    def testUSBPollerThreadException(self):
        """
        USBPollerThread exception handling.
        """
        class FakeEventPoll(PollDetector):
            # pylint: disable=method-hidden
            def poll(self, *args, **kw):
                self.poll = super(FakeEventPoll, self).poll
                return ['dummy']
            # pylint: enable=method-hidden
        with USBContext() as context:
            def fakeHandleEventsLocked():
                raise usb1.USBError(0)
            context.handleEventsLocked = fakeHandleEventsLocked
            exception_event = threading.Event()
            exception_list = []
            def exceptionHandler(exc):
                exception_list.append(exc)
                exception_event.set()
            try:
                poller = usb1.USBPollerThread(
                    context, FakeEventPoll(), exceptionHandler)
            except OSError:
                raise unittest.SkipTest('libusb without file descriptor events')
            poller.start()
            exception_event.wait(1)
            self.assertTrue(exception_list, exception_list)
            self.assertTrue(poller.is_alive())

    @staticmethod
    def testDescriptors():
        """
        Test descriptor walk.
        Needs any usb device, which won't be opened.
        """
        with USBContext() as context:
            device_list = context.getDeviceList(skip_on_error=True)
            found = False
            for device in device_list:
                device.getBusNumber()
                device.getPortNumber()
                device.getPortNumberList()
                device.getDeviceAddress()
                for settings in device.iterSettings():
                    for endpoint in settings:
                        pass
                for configuration in device.iterConfigurations():
                    for interface in configuration:
                        for settings in interface:
                            for endpoint in settings:
                                found = True
            if not found:
                raise unittest.SkipTest('descriptor walk test did not complete')

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

    def testUSBTransferMayRaiseUSBError(self):
        """
        mayRaiseUSBError needs to be a class property to be reliably able
        to call it during interpreter shutdown. But setting a function as
        property makes it bound to the instance when accessed. This is not
        obviously visible because mayRaiseUSBError has a should-never-be-used
        second argument for exactly the same purpose, but which accidentally
        receives the value intended as the first parameter (the first parameter
        being replaced by "self" as for any bound method).
        So this test verifies that USBTranfer.__mayRaiseUSBError behaves the
        intended way.
        And to make this test work when there is no USB device around, directly
        instanciate USBTransfer and access tested private property.
        """
        transfer = usb1.USBTransfer(None, 0, None, None)
        transfer._USBTransfer__mayRaiseUSBError(0)
        self.assertRaises(usb1.USBErrorIO, transfer._USBTransfer__mayRaiseUSBError, usb1.ERROR_IO)

if __name__ == '__main__':
    unittest.main()
