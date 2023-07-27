#!/usr/bin/env python3

import click
import usb.core
import usb.util

class DeviceException(Exception):
    pass


class ReadException(Exception):
    pass

class BasedIntParamType(click.ParamType):
    name = "integer"

    def convert(self, value, param, ctx):
        if isinstance(value, int):
            return value

        try:
            if value[:2].lower() == "0x":
                return int(value[2:], 16)
            elif value[:1] == "0":
                return int(value, 8)
            return int(value, 10)
        except ValueError:
            self.fail(f"{value!r} is not a valid integer", param, ctx)

BASED_INT = BasedIntParamType()

@click.command(help="Replacement for MINI KeyBoard v02.1.1")
@click.option("-V", "--vendor-id", "vendor_id", type=BASED_INT, default="0x1189", help="USB Vendor ID")
@click.option("-P", "--product-id", "product_id", type=BASED_INT, default="0x8890", help="USB Product ID")
@click.option("-E", "--edpoint-id", "endpoint_id", type=BASED_INT, default="0x8890", help="USB End")
@click.option("-l", "--led-mode", "led_mode", type=click.INT, default=None, help="LED Mode 0,1,2")
@click.option("-k", "--key", "key_number", type=click.INT, default=None, help="Key to program")

def main(vendor_id, product_id, endpoint_id, led_mode, key_number):
    # find keyboard
    dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)

    # was it found?
    if dev is None:
        raise ValueError('Device not found')

    # Select configuration endpoint (0x2)
    ep = dev[0].interfaces()[1].endpoints()[0]

    # Detach, if required
    attach_kernel_driver = []
    for interface in [0,2,3]:
        if dev.is_kernel_driver_active(interface):
                try:
                    dev.detach_kernel_driver(interface)
                    dev.reset()
                    attach_kernel_driver.append(interface)
                except usb.core.USBError as e:
                    raise DeviceException('Could not detach kernel driver: %s' % str(e))

    # Enable configuration
    try:
        dev.set_configuration()
    except usb.core.USBError as e:
        raise DeviceException('Could not set configuration: %s' % str(e))

    eaddr = ep.bEndpointAddress

    # Configure LED Mode
    if led_mode is not None:
        # Set device into configuraiton mode
        dev.write(eaddr, [0x03,0xa1,0x01])
        # Configure LED
        dev.write(eaddr, [0x03,0xb0,0x18,led_mode])
        # Disable configuration mode
        dev.write(eaddr, [0x03,0xaa,0xa1])


    # Restore kernel driver
    for interface in attach_kernel_driver:
        try:
            dev.attach_kernel_driver(interface)
        except usb.core.USBError as e:
            raise DeviceException('Could not attach kernel driver: %s' % str(e))

if __name__ == "__main__":
    exit(main())
