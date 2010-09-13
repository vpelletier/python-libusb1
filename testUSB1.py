import unittest
import usb1
import libusb1
from ctypes import pointer

class USBTransferTests(unittest.TestCase):
    def getTransfer(self, iso_packets=0):
        # Dummy handle
        return usb1.USBTransfer(pointer(libusb1.libusb_device_handle()),
            iso_packets)

    def testSetControl(self):
        """
        Simplest test: feed some data, must not raise.
        """
        transfer = self.getTransfer()
        request_type = libusb1.LIBUSB_TYPE_STANDARD
        request = libusb1.LIBUSB_REQUEST_GET_STATUS
        value = 0
        index = 0
        buff = '\x00\xff'
        buff_len = 2
        def callback(transfer):
            pass
        user_data = []
        timeout = 1000

        # All provided, buffer variant
        transfer.setControl(request_type, request, value, index, buff,
            callback=callback, user_data=user_data, timeout=timeout)
        self.assertEqual(buff, transfer.getBuffer())
        self.assertRaises(ValueError, transfer.setBuffer, buff)
        # All provided, buffer length variant
        transfer.setControl(request_type, request, value, index, buff_len,
            callback=callback, user_data=user_data, timeout=timeout)
        # No timeout
        transfer.setControl(request_type, request, value, index, buff,
            callback=callback, user_data=user_data)
        # No user data
        transfer.setControl(request_type, request, value, index, buff,
            callback=callback)
        # No callback
        transfer.setControl(request_type, request, value, index, buff)

    def _testSetBulkOrInterrupt(self, setter_id):
        transfer = self.getTransfer()
        endpoint = 0x81
        buff = '\x00\xff'
        buff_len = 2
        other_buff = 'foo'
        def callback(transfer):
            pass
        user_data = []
        timeout = 1000
        setter = getattr(transfer, setter_id)
        # All provided, buffer variant
        setter(endpoint, buff, callback=callback, user_data=user_data,
            timeout=timeout)
        self.assertEqual(buff, transfer.getBuffer())
        transfer.setBuffer(other_buff)
        self.assertEqual(other_buff, transfer.getBuffer())
        transfer.setBuffer(buff_len)
        self.assertEqual(buff_len, len(transfer.getBuffer()))
        # All provided, buffer length variant
        setter(endpoint, buff_len, callback=callback, user_data=user_data,
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
        self._testSetBulkOrInterrupt('setBulk')

    def testSetInterrupt(self):
        """
        Simplest test: feed some data, must not raise.
        Also, test setBuffer/getBuffer.
        """
        self._testSetBulkOrInterrupt('setInterrupt')

    def testSetGetCallback(self):
        transfer = self.getTransfer()
        def callback(transfer):
            pass
        transfer.setCallback(callback)
        got_callback = transfer.getCallback()
        self.assertEqual(callback, got_callback)

if __name__ == '__main__':
    unittest.main()
