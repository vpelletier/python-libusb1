#!/usr/bin/env python
import usb1

def main():
    context = usb1.USBContext()
    for device in context.getDeviceList(skip_on_error=True):
        print 'ID %04x:%04x' % (device.getVendorID(), device.getProductID()), '->'.join(str(x) for x in ['Bus %03i' % (device.getBusNumber(), )] + device.getPortNumberList()), 'Device', device.getDeviceAddress()

if __name__ == '__main__':
    main()
