#!/usr/bin/env python
import usb1
import libusb1

def hotplug_callback(context, device, event):
    print "Device %s: %s" % (
        {
            libusb1.LIBUSB_HOTPLUG_EVENT_DEVICE_ARRIVED: 'arrived',
            libusb1.LIBUSB_HOTPLUG_EVENT_DEVICE_LEFT: 'left',
        }[event],
        device,
    )

def main():
    context = usb1.USBContext()
    if not context.hasCapability(libusb1.LIBUSB_CAP_HAS_HOTPLUG):
        print 'Hotplug support is missing. Please upgdate your libusb version.'
        return
    opaque = context.hotplugRegisterCallback(hotplug_callback)
    try:
        while True:
            context.handleEvents()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == '__main__':
    main()
