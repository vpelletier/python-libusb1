#!/usr/bin/env python
# Copyright (C) 2013-2015  Vincent Pelletier <plr.vincent@gmail.com>
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
