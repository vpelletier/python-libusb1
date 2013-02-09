#!/usr/bin/env python
import usb1

def main():
    context = usb1.USBContext()
    for device in context.getDeviceList(skip_on_error=True):
        print str(device)

if __name__ == '__main__':
    main()
