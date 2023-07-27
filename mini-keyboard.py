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


def usb_write(dev, endpoint_addr, data):
    if True:
        hex = []
        for d in data:
            hex.append("0x%02x" % d)
        print("USB Write: EP=0x%02x DATA=%s" % (endpoint_addr, ','.join(hex)))
    dev.write(endpoint_addr,data)


@click.command(help="Replacement for MINI KeyBoard v02.1.1")

@click.option("-V", "--vendor-id", "vendor_id", type=BASED_INT, default="0x1189", help="USB Vendor ID default: 0x1189")
@click.option("-P", "--product-id", "product_id", type=BASED_INT, default="0x8890", help="USB Product ID default: 0x8890")
@click.option("-E", "--edpoint-id", "endpoint_addr", type=BASED_INT, default="0x02", help="USB Endpoint Address default: 0x02")

@click.option("-l", "--led-mode", "led_mode", type=click.INT, default=None, help="LED Mode 0,1,2")

@click.option("-k", "--key", "key_number", type=click.INT, default=None, help="Key to program")
@click.option("-l", "--layer", "key_layer", type=click.INT, default=1, help="Key layer [1-3]")
@click.option("-m", "--key-mode", "key_mode", type=click.STRING, default="key", help="Key Mode: key,mouse,multimedia")

@click.option("--mouse-buttons", "mouse_button", type=click.STRING, default='', help="Mouse Button(s): LEFT,MIDDLE,RIGHT")
@click.option("--mouse-move-x", "mouse_move_x", type=click.IntRange(-127,127), default=0, help="Mouse movement horizontal -127..0..127")
@click.option("--mouse-move-y", "mouse_move_y", type=click.IntRange(-127,127), default=0, help="Mouse movement vertical -127..0..127")

def main(vendor_id, product_id, endpoint_addr, led_mode, key_number, key_layer, key_mode, mouse_button, mouse_move_x, mouse_move_y):
    # find keyboard
    dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)

    # was it found?
    if dev is None:
        raise ValueError('Device not found')

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


    # Calculate some values
    key_layer = key_layer << 4

    # Configure Key
    if key_number is not None:
        # Set device into configuraiton mode
        usb_write(dev, endpoint_addr, [0x03,0xa1,0x01])

        if key_mode == 'key':
            for s in range(8):
                usb_write(dev, endpoint_addr, [0x03,key_number, key_layer + 0x01,0x06, s, 0x10, 0x00, 0x00])
                usb_write(dev, endpoint_addr, [0x03,key_number+1,0x11,0x06, s, 0x20, 0x00, 0x00])
                usb_write(dev, endpoint_addr, [0x03,key_number+2,0x11,0x06, s, 0x40, 0x00, 0x00])
                usb_write(dev, endpoint_addr, [0x03,key_number+3,0x11,0x06, s, 0x80, 0x00, 0x00])

        if key_mode == 'mouse':
            # Calculate Buttons
            # 0x01    Left Click
            # 0x02    Right Click
            # 0x04    Middle Click
            btn = 0
            btns = mouse_button.lower().split(',')
            if 'left' in btns:
                btn = btn + 0x01
            if 'right' in btns:
                btn = btn + 0x02
            if 'middle' in btns:
                btn = btn + 0x04
            if mouse_move_x < 0:
                mouse_move_x = 255-abs(mouse_move_x)
            if mouse_move_y < 0:
                mouse_move_y = 255-abs(mouse_move_y)
            usb_write(dev, endpoint_addr, [0x03,key_number , key_layer + 0x03, btn, mouse_move_x, mouse_move_y, 0x00])

        if key_mode == 'multimedia':
            #
            usb_write(dev, endpoint_addr, [0x03,key_number , key_layer + 0x02, 0xe2, 0x00])


        # Disable configuration mode
        usb_write(dev,endpoint_addr, [0x03,0xaa,0xaa])



    # Configure LED Mode
    if led_mode is not None:
        # Set device into configuraiton mode
        dev.write(endpoint_addr, [0x03,0xa1,0x01])
        # Configure LED
        dev.write(endpoint_addr, [0x03,0xb0,0x18,led_mode])
        # Disable configuration mode
        dev.write(endpoint_addr, [0x03,0xaa,0xa1])


    # Restore kernel driver
    for interface in attach_kernel_driver:
        try:
            dev.attach_kernel_driver(interface)
        except usb.core.USBError as e:
            raise DeviceException('Could not attach kernel driver: %s' % str(e))

if __name__ == "__main__":
    exit(main())
