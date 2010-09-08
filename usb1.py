# pyusb compatibility layer for libus-1.0
import libusb1
from ctypes import byref, create_string_buffer, c_int, sizeof, POINTER, \
    create_unicode_buffer, c_wchar, cast, c_uint16, c_ubyte
from cStringIO import StringIO

__all__ = ['LibUSBContext']

# Default string length
# From a comment in libusb-1.0: "Some devices choke on size > 255"
STRING_LENGTH = 255

EVENT_CALLBACK_SET = frozenset((
  libusb1.LIBUSB_TRANSFER_COMPLETED,
  libusb1.LIBUSB_TRANSFER_ERROR,
  libusb1.LIBUSB_TRANSFER_TIMED_OUT,
  libusb1.LIBUSB_TRANSFER_CANCELLED,
  libusb1.LIBUSB_TRANSFER_STALL,
  libusb1.LIBUSB_TRANSFER_NO_DEVICE,
  libusb1.LIBUSB_TRANSFER_OVERFLOW,
))

DEFAULT_ASYNC_TRANSFER_ERROR_CALLBACK = lambda x, y: False

class USBAsyncReaderBase(object):
    _handle = None
    _submited = False

    def __init__(self, handle, endpoint, size, user_data=None, timeout=0):
        data = create_string_buffer(size)
        self._data = data
        self._transfer = self._getTransfer(
          handle,
          endpoint,
          data,
          self._callbackDispatcher,
          user_data,
          timeout,
        )
        # XXX: set _handle *after* _transfer, so __del__ doesn't get an
        # exception if called during constructor execution.
        self._handle = handle
        self._event_callback_dict = {}
        self._errorCallback = DEFAULT_ASYNC_TRANSFER_ERROR_CALLBACK

    def submit(self):
        self._submited = True
        self._handle.submitTransfer(self._transfer)

    def cancel(self):
        self._handle.cancelTransfer(self._transfer)
        self._submited = False

    def setEventCallback(self, event, callback):
        if event not in EVENT_CALLBACK_SET:
            raise ValueError, 'Unknown event %r.' % (event, )
        self._event_callback_dict[event] = callback

    def setDefaultCallback(self, callback):
        self._errorCallback = callback

    def getEventCallback(self, event, default=None):
        return self._event_callback_dict.get(event, default)

    def _callbackDispatcher(self, transfer_p):
        transfer = self._transfer.contents #transfer_p.contents
        if self.getEventCallback(transfer.status, self._errorCallback)(
            transfer, self._data):
            self.submit()
        else:
            self._submited = False

    def isSubmited(self):
        return self._submited

    def __del__(self):
        if self._handle is not None:
            try:
                self.cancel()
            except libusb1.USBError, exception:
                if exception.value != libusb1.LIBUSB_ERROR_NOT_FOUND:
                    raise

class USBAsyncBulkReader(USBAsyncReaderBase):
    def _getTransfer(self, handle, *args, **kw):
        return handle.getBulkTransfer(*args, **kw)

class USBAsyncInterruptReader(USBAsyncReaderBase):
    def _getTransfer(self, handle, *args, **kw):
        return handle.getInterruptTransfer(*args, **kw)

class USBPoller(object):
    def __init__(self, context, poller):
        self.context = context
        self.poller = poller
        fd_set = set()
        self.fd_set = fd_set
        context.setPollFDNotifiers(self._registerFD, self._unregisterFD)
        for fd, events in context.getPollFDList():
            self._registerFD(fd, events)

    def poll(self, timeout=None):
        fd_set = self.fd_set
        next_usb_timeout = self.context.getNextTimeout()
        if next_usb_timeout == 0:
            next_usb_timeout = None
        if timeout is None:
            usb_timeout = next_usb_timeout
        else:
            usb_timeout = min(next_usb_timeout or timeout, timeout)
        event_list = self.poller.poll(usb_timeout)
        event_list_len = len(event_list)
        if event_list_len:
            result = [(x, y) for x, y in event_list if x not in fd_set]
            if len(result) != event_list_len:
                self.context.handleEventsTimeout()
        else:
            result = event_list
            self.context.handleEventsTimeout()
        return result

    def register(self, fd, events):
        self.poller.register(fd, events)

    def unregister(self, fd):
        self.poller.unregister(fd)

    def _registerFD(self, fd, events, user_data=None):
        self.fd_set.add(fd)
        self.register(fd, events)

    def _unregisterFD(self, fd, user_data=None):
        self.unregister(fd)
        self.sd_set.discard(fd)

class USBDeviceHandle(object):
    handle = None

    def __init__(self, context, handle):
        # XXX Context parameter is just here as a hint for garbage collector:
        # It must collect USBDeviceHandle instance before their LibUSBContext.
        self.context = context
        self.handle = handle

    def __del__(self):
        self.close()

    def close(self):
        handle = self.handle
        if handle is not None:
            libusb1.libusb_close(handle)
            self.handle = None

    def getConfiguration(self):
        configuration = c_int()
        result = libusb1.libusb_get_configuration(self.handle,
                                                  byref(configuration))
        if result:
            raise libusb1.USBError, result
        return configuration

    def setConfiguration(self, configuration):
        result = libusb1.libusb_set_configuration(self.handle, configuration)
        if result:
            raise libusb1.USBError, result

    def claimInterface(self, interface):
        result = libusb1.libusb_claim_interface(self.handle, interface)
        if result:
            raise libusb1.USBError, result

    def releaseInterface(self, interface):
        result = libusb1.libusb_release_interface(self.handle, interface)
        if result:
            raise libusb1.USBError, result

    def setInterfaceAltSetting(self, interface, alt_setting):
        result = libusb1.libusb_set_interface_alt_setting(self.handle,
                                                          interface,
                                                          alt_setting)
        if result:
            raise libusb1.USBError, result

    def clearHalt(self, endpoint):
        result = libusb1.libusb_clear_halt(self.handle, endpoint)
        if result:
            raise libusb1.USBError, result

    def resetDevice(self):
        result = libusb1.libusb_reset_device(self.handle)
        if result:
            raise libusb1.USBError, result

    def kernelDriverActive(self, interface):
        result = libusb1.libusb_kernel_driver_active(self.handle, interface)
        if result == 0:
            is_active = False
        elif result == 1:
            is_active = True
        else:
            raise libusb1.USBError, result
        return is_active

    def detachKernelDriver(self, interface):
        result = libusb1.libusb_detach_kernel_driver(self.handle, interface)
        if result:
            raise libusb1.USBError, result

    def attachKernelDriver(self, interface):
        result = libusb1.libusb_attach_kernel_driver(self.handle, interface)
        if result:
            raise libusb1.USBError, result

    def getSupportedLanguageList(self):
        descriptor_string = create_string_buffer(STRING_LENGTH)
        result = libusb1.libusb_get_string_descriptor(self.handle,
            0, 0, descriptor_string, sizeof(descriptor_string))
        if result < 0:
            if result == libusb1.LIBUSB_ERROR_PIPE:
                # From libusb_control_transfer doc:
                # control request not supported by the device
                return []
            raise libusb1.USBError, result
        length = cast(descriptor_string, POINTER(c_ubyte))[0]
        langid_list = cast(descriptor_string, POINTER(c_uint16))
        result = []
        append = result.append
        for offset in xrange(1, length / 2):
            append(libusb1.libusb_le16_to_cpu(langid_list[offset]))
        return result

    def getStringDescriptor(self, descriptor, lang_id):
        descriptor_string = create_unicode_buffer(
            STRING_LENGTH / sizeof(c_wchar))
        result = libusb1.libusb_get_string_descriptor(self.handle,
            descriptor, lang_id, descriptor_string, sizeof(descriptor_string))
        if result < 0:
            raise libusb1.USBError, result
        return descriptor_string.value

    def getASCIIStringDescriptor(self, descriptor):
        descriptor_string = create_string_buffer(STRING_LENGTH)
        result = libusb1.libusb_get_string_descriptor_ascii(self.handle,
             descriptor, descriptor_string, sizeof(descriptor_string))
        if result < 0:
            raise libusb1.USBError, result
        return descriptor_string.value

    # Sync I/O

    def _controlTransfer(self, request_type, request, value, index, data,
                         length, timeout):
        result = libusb1.libusb_control_transfer(self.handle, request_type,
            request, value, index, data, length, timeout)
        if result < 0:
            raise libusb1.USBError, result
        return result

    def controlWrite(self, request_type, request, value, index, data,
                     timeout=0):
        request_type = (request_type & ~libusb1.USB_ENDPOINT_DIR_MASK) | \
                        libusb1.LIBUSB_ENDPOINT_OUT
        data = create_string_buffer(data)
        return self._controlTransfer(request_type, request, value, index, data,
                                     len(data)-1, timeout)

    def controlRead(self, request_type, request, value, index, length,
                    timeout=0):
        request_type = (request_type & ~libusb1.USB_ENDPOINT_DIR_MASK) | \
                        libusb1.LIBUSB_ENDPOINT_IN
        data = create_string_buffer(length)
        transferred = self._controlTransfer(request_type, request, value,
                                            index, data, length, timeout)
        return data.raw[:transferred]

    def _bulkTransfer(self, endpoint, data, length, timeout):
        transferred = c_int()
        result = libusb1.libusb_bulk_transfer(self.handle, endpoint,
            data, length, byref(transferred), timeout)
        if result:
            raise libusb1.USBError, result
        return transferred.value

    def bulkWrite(self, endpoint, data, timeout=0):
        endpoint = (endpoint & ~libusb1.USB_ENDPOINT_DIR_MASK) | \
                    libusb1.LIBUSB_ENDPOINT_OUT
        data = create_string_buffer(data)
        return self._bulkTransfer(endpoint, data, len(data) - 1, timeout)

    def bulkRead(self, endpoint, length, timeout=0):
        endpoint = (endpoint & ~libusb1.USB_ENDPOINT_DIR_MASK) | \
                    libusb1.LIBUSB_ENDPOINT_IN
        data = create_string_buffer(length)
        transferred = self._bulkTransfer(endpoint, data, length, timeout)
        return data.raw[:transferred]

    def _interruptTransfer(self, endpoint, data, length, timeout):
        transferred = c_int()
        result = libusb1.libusb_interrupt_transfer(self.handle, endpoint,
            data, length, byref(transferred), timeout)
        if result:
            raise libusb1.USBError, result
        return transferred.value

    def interruptWrite(self, endpoint, data, timeout=0):
        endpoint = (endpoint & ~libusb1.USB_ENDPOINT_DIR_MASK) | \
                    libusb1.LIBUSB_ENDPOINT_OUT
        data = create_string_buffer(data)
        return self._interruptTransfer(endpoint, data, len(data) - 1, timeout)

    def interruptRead(self, endpoint, length, timeout=0):
        endpoint = (endpoint & ~libusb1.USB_ENDPOINT_DIR_MASK) | \
                    libusb1.LIBUSB_ENDPOINT_IN
        data = create_string_buffer(length)
        transferred = self._interruptTransfer(endpoint, data, length, timeout)
        return data.raw[:transferred]

    def _getTransfer(self, iso_packets=0):
        result = libusb1.libusb_alloc_transfer(iso_packets)
        if not result:
            raise libusb1.USBError, 'Unable to get a transfer object'
        return result

    def fillBulkTransfer(self, transfer, endpoint, string_buffer,
                         callback, user_data, timeout):
        libusb1.libusb_fill_bulk_transfer(transfer, self.handle,
            endpoint, string_buffer, sizeof(string_buffer),
            libusb1.libusb_transfer_cb_fn_p(callback), user_data,
            timeout)

    def getBulkTransfer(self, endpoint, string_buffer, callback,
                        user_data=None, timeout=0):
        result = self._getTransfer()
        self.fillBulkTransfer(result, endpoint, string_buffer, callback,
            user_data, timeout)
        return result

    def fillInterruptTransfer(self, transfer, endpoint, string_buffer,
                              callback, user_data, timeout):
        libusb1.libusb_fill_interrupt_transfer(transfer, self.handle,
            endpoint, string_buffer,  sizeof(string_buffer),
            libusb1.libusb_transfer_cb_fn_p(callback), user_data,
            timeout)

    def getInterruptTransfer(self, endpoint, string_buffer, callback,
                             user_data=None, timeout=0):
        result = self._getTransfer()
        self.fillInterruptTransfer(result, endpoint, string_buffer,
            callback, user_data, timeout)
        return result

    def fillControlSetup(self, string_buffer, request_type, request, value,
                         index, length):
        libusb1.libusb_fill_control_setup(string_buffer, request_type,
            request, value, index, length)

    def fillControlTransfer(self, transfer, setup, callback,
                            user_data, timeout):
        libusb1.libusb_fill_control_transfer(transfer, self.handle,
            setup, libusb1.libusb_transfer_cb_fn_p(callback), user_data,
            timeout)

    def getControlTransfer(self, setup, callback, user_data=None, timeout=0):
        result = self._getTransfer()
        self.fillControlTransfer(result, setup, callback, user_data, timeout)
        return result

    def fillISOTransfer(self, *args, **kw):
        raise NotImplementedError

    def getISOTransfer(self, *args, **kw):
        raise NotImplementedError

    def submitTransfer(self, transfer):
        result = libusb1.libusb_submit_transfer(transfer)
        if result:
            raise libusb1.USBError, result

    def cancelTransfer(self, transfer):
        result = libusb1.libusb_cancel_transfer(transfer)
        if result:
            raise libusb1.USBError, result

class USBDevice(object):

    configuration_descriptor_list = None

    def __init__(self, context, device_p):
        self.context = context
        libusb1.libusb_ref_device(device_p)
        self.device_p = device_p
        # Fetch device descriptor
        device_descriptor = libusb1.libusb_device_descriptor()
        result = libusb1.libusb_get_device_descriptor(device_p,
            byref(device_descriptor))
        if result:
            raise libusb1.USBError, result
        self.device_descriptor = device_descriptor
        # Fetch all configuration descriptors
        self.configuration_descriptor_list = []
        append = self.configuration_descriptor_list.append
        for configuration_id in xrange(device_descriptor.bNumConfigurations):
            config = libusb1.libusb_config_descriptor_p()
            result = libusb1.libusb_get_config_descriptor(device_p,
                configuration_id, byref(config))
            if result:
                raise libusb1.USBError, result
            append(config.contents)

    def __del__(self):
        libusb1.libusb_unref_device(self.device_p)
        if self.configuration_descriptor_list is not None:
            for config in self.configuration_descriptor_list:
                libusb1.libusb_free_config_descriptor(byref(config))

    def __str__(self):
        return 'Bus %03i Device %03i: ID %04x:%04x %s %s' % (
            self.getBusNumber(),
            self.getDeviceAddress(),
            self.getVendorID(),
            self.getProductID(),
            self.getManufacturer(),
            self.getProduct()
        )

    def reprConfigurations(self):
        out = StringIO()
        for config in self.configuration_descriptor_list:
            print >> out, 'Configuration %i: %s' % (config.bConfigurationValue,
                self._getASCIIStringDescriptor(config.iConfiguration))
            print >> out, '  Max Power: %i mA' % (config.MaxPower * 2, )
            # TODO: bmAttributes dump
            for interface_num in xrange(config.bNumInterfaces):
                interface = config.interface[interface_num]
                print >> out, '  Interface %i' % (interface_num, )
                for alt_setting_num in xrange(interface.num_altsetting):
                    altsetting = interface.altsetting[alt_setting_num]
                    print >> out, '    Alt Setting %i: %s' % (alt_setting_num,
                        self._getASCIIStringDescriptor(altsetting.iInterface))
                    print >> out, '      Class: %02x Subclass: %02x' % \
                        (altsetting.bInterfaceClass,
                         altsetting.bInterfaceSubClass)
                    print >> out, '      Protocol: %02x' % \
                        (altsetting.bInterfaceProtocol, )
                    for endpoint_num in xrange(altsetting.bNumEndpoints):
                        endpoint = altsetting.endpoint[endpoint_num]
                        print >> out, '      Endpoint %i' % (endpoint_num, )
                        print >> out, '        Address: %02x' % \
                            (endpoint.bEndpointAddress, )
                        attribute_list = []
                        transfer_type = endpoint.bmAttributes & \
                            libusb1.LIBUSB_TRANSFER_TYPE_MASK
                        attribute_list.append(libusb1.libusb_transfer_type(
                            transfer_type
                        ))
                        if transfer_type == \
                            libusb1.LIBUSB_TRANSFER_TYPE_ISOCHRONOUS:
                            attribute_list.append(libusb1.libusb_iso_sync_type(
                                (endpoint.bmAttributes & \
                                 libusb1.LIBUSB_ISO_SYNC_TYPE_MASK) >> 2
                            ))
                            attribute_list.append(libusb1.libusb_iso_usage_type(
                                (endpoint.bmAttributes & \
                                 libusb1.LIBUSB_ISO_USAGE_TYPE_MASK) >> 4
                            ))
                        print >> out, '        Attributes: %s' % \
                            (', '.join(attribute_list), )
                        print >> out, '        Max Packet Size: %i' % \
                            (endpoint.wMaxPacketSize, )
                        print >> out, '        Interval: %i' % \
                            (endpoint.bInterval, )
                        print >> out, '        Refresh: %i' % \
                            (endpoint.bRefresh, )
                        print >> out, '        Sync Address: %02x' % \
                            (endpoint.bSynchAddress, )
        return out.getvalue()

    def getBusNumber(self):
        return libusb1.libusb_get_bus_number(self.device_p)

    def getDeviceAddress(self):
        return libusb1.libusb_get_device_address(self.device_p)

    def getbcdUSB(self):
        return self.device_descriptor.bcdUSB

    def getDeviceClass(self):
        return self.device_descriptor.bDeviceClass

    def getDeviceSubClass(self):
        return self.device_descriptor.bDeviceSubClass

    def getDeviceProtocol(self):
        return self.device_descriptor.bDeviceProtocol

    def getMaxPacketSize0(self):
        return self.device_descriptor.bMaxPacketSize0

    def getVendorID(self):
        return self.device_descriptor.idVendor

    def getProductID(self):
        return self.device_descriptor.idProduct

    def getbcdDevice(self):
        return self.device_descriptor.bcdDevice

    def getSupportedLanguageList(self):
        temp_handle = self.open()
        return temp_handle.getSupportedLanguageList()

    def _getStringDescriptor(self, descriptor, lang_id):
        if descriptor == 0:
            result = None
        else:
            temp_handle = self.open()
            result = temp_handle.getStringDescriptor(descriptor, lang_id)
        return result

    def _getASCIIStringDescriptor(self, descriptor):
        if descriptor == 0:
            result = None
        else:
            temp_handle = self.open()
            result = temp_handle.getASCIIStringDescriptor(descriptor)
        return result

    def getManufacturer(self):
        return self._getASCIIStringDescriptor(
            self.device_descriptor.iManufacturer)

    def getProduct(self):
        return self._getASCIIStringDescriptor(self.device_descriptor.iProduct)

    def getSerialNumber(self):
        return self.device_descriptor.iSerialNumber

    def getNumConfigurations(self):
        return self.device_descriptor.bNumConfigurations

    def open(self):
        handle = libusb1.libusb_device_handle_p()
        result = libusb1.libusb_open(self.device_p, byref(handle))
        if result:
            raise libusb1.USBError, result
        return USBDeviceHandle(self.context, handle)

class LibUSBContext(object):

    context_p = None

    def __init__(self):
        context_p = libusb1.libusb_context_p()
        result = libusb1.libusb_init(byref(context_p))
        if result:
            raise libusb1.USBError, result
        self.context_p = context_p

    def __del__(self):
        self.exit()

    def exit(self):
        context_p = self.context_p
        if context_p is not None:
            libusb1.libusb_exit(context_p)
            self.context_p = None

    def getDeviceList(self):
        device_p_p = libusb1.libusb_device_p_p()
        device_list_len = libusb1.libusb_get_device_list(self.context_p,
                                                         byref(device_p_p))
        result = [USBDevice(self, x) for x in device_p_p[:device_list_len]]
        # XXX: causes problems, why ?
        #libusb1.libusb_free_device_list(device_p_p, 1)
        return result

    def openByVendorIDAndProductID(self, vendor_id, product_id):
        handle_p = libusb1.libusb_open_device_with_vid_pid(self.context_p,
            vendor_id, product_id)
        if handle_p:
            result = USBDeviceHandle(self, handle_p)
        else:
            result = None
        return result

    def getPollFDList(self):
        pollfd_p_p = libusb1.libusb_get_pollfds(self.context_p)
        result = []
        append = result.append
        fd_index = 0
        while pollfd_p_p[fd_index]:
            append((pollfd_p_p[fd_index].contents.fd,
                    pollfd_p_p[fd_index].contents.events))
            fd_index += 1
        # XXX: causes problems, why ?
        #libusb1.libusb.free(pollfd_p_p)
        return result

    def handleEvents(self):
        result = libusb1.libusb_handle_events(self.context_p)
        if result:
            raise libusb1.USBError, result

    def handleEventsTimeout(self, tv=None):
        assert tv is None, 'tv parameter is not supported yet'
        tv = libusb1.timeval(0, 0)
        result = libusb1.libusb_handle_events_timeout(self.context_p, byref(tv))
        if result:
            raise libusb1.USBError, result

    def setPollFDNotifiers(self, added_cb=None, removed_cb=None, user_data=None):
        if added_cb is None:
          added_cb = POINTER(None)
        else:
          added_cb = libusb1.libusb_pollfd_added_cb_p(added_cb)
        if removed_cb is None:
          removed_cb = POINTER(None)
        else:
          removed_cb = libusb1.libusb_pollfd_removed_cb_p(removed_cb)
        libusb1.libusb_set_pollfd_notifiers(self.context_p, added_cb,
                                            removed_cb, user_data)

    def getNextTimeout(self):
        return libusb1.libusb_get_next_timeout(self.context_p, None)

