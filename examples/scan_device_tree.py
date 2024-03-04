"""
python-libusb1 device tree scan example.
This program shows the entire tree of devices/configurations/interfaces/endpoints
that are available on your computer.  It should be useful when interfacing with a
new USB device (since you can easily examine what features are available on the device).
"""

import usb1

def scan_device_tree():
    with usb1.USBContext() as context:
        for dev in context.getDeviceIterator(skip_on_error=True):
            dev: usb1.USBDevice

            try:
                print(
                    f"- Device: {dev.getVendorID():04x}:{dev.getProductID():04x}, {dev.getManufacturer()} {dev.getProduct()}, SerNo: {dev.getSerialNumber()}"
                )
            except usb1.USBError:
                print(
                    f"- Device: {dev.getVendorID():04x}:{dev.getProductID():04x} <failed to open, on Windows this is because it does not have the WinUSB driver attached>"
                )

            for cfg in dev:
                # Note: for docs on USBConfiguration, see here: https://libusb.sourceforge.io/api-1.0/structlibusb__config__descriptor.html
                # Also see https://www.beyondlogic.org/usbnutshell/usb5.shtml#ConfigurationDescriptors
                cfg: usb1.USBConfiguration
                print(
                    f"---> Cfg: Num Interfaces: {cfg.getNumInterfaces()}, Identifier: {cfg.getConfigurationValue()}, "
                    f"Attributes: 0x{cfg.getAttributes():02x}"
                )

                for iface_idx, iface in enumerate(cfg):
                    iface: usb1.USBInterface

                    print(f"    ---> Interface {iface_idx}")

                    for altsetting_idx, altsetting in enumerate(iface):
                        altsetting: usb1.USBInterfaceSetting

                        # The docs for USBInterfaceSetting can be seen here:
                        # https://libusb.sourceforge.io/api-1.0/structlibusb__interface__descriptor.html
                        # For an enumeration of defined class, subclass, and protocol values, see here:
                        # https://www.usb.org/defined-class-codes

                        print(
                            f"        ---> Alternate settings {altsetting_idx}: Num Endpoints: {altsetting.getNumEndpoints()}, "
                            f"Class and SubClass: (0x{altsetting.getClass():02x}, 0x{altsetting.getSubClass():02x}), "
                            f"Protocol: {altsetting.getProtocol()}"
                        )

                        for endpoint in altsetting:
                            endpoint: usb1.USBEndpoint

                            # The docs for USBEndpoint can be seen here:
                            # https://libusb.sourceforge.io/api-1.0/structlibusb__endpoint__descriptor.html#a111d087a09cbeded8e15eda9127e23d2

                            # Process attributes field
                            if endpoint.getAttributes() & 3 == 0:
                                ep_type = "Control"
                            elif endpoint.getAttributes() & 3 == 1:
                                ep_type = "Isochronous"
                            elif endpoint.getAttributes() & 3 == 2:
                                ep_type = "Bulk"
                            else:
                                ep_type = "Interrupt"

                            print(
                                f"            ---> Endpoint 0x{endpoint.getAddress():02x}: Direction: "
                                f"{'Dev-To-Host' if endpoint.getAddress() & 0x80 != 0 else 'Host-To-Dev'}, Type: {ep_type}"
                            )


if __name__ == '__main__':
    scan_device_tree()
