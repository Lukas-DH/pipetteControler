#!/usr/bin/env python3
"""
Configuration file for pipette integration system
Edit these values for your specific setup
"""

# Serial port configuration
# Common ports:
#   macOS: "/dev/tty.usbserial-FT3LK3ZO"
#   Linux(jetsonNano): "/dev/ttyUSB0"
#   Windows: "COM3"
PIPETTE_PORT = "/dev/tty.usbserial-FT3LK3ZO"
PIPETTE_PORT_2 = "/dev/tty.usbserial-FTXKT5V3"  # Update this for your second pipette

# Modbus server configuration
MODBUS_HOST = "localhost"
MODBUS_PORT = 502

# Pipette 1 default parameters
DEFAULT_ASPIRATE_VOLUME = 5000
DEFAULT_DISPENSE_VOLUME = 1250
DEFAULT_SPEED = 5
DEFAULT_TIMEOUT = 60

# Pipette 2 default parameters
DEFAULT_ASPIRATE_VOLUME_2 = 5000
DEFAULT_DISPENSE_VOLUME_2 = 1250
DEFAULT_SPEED_2 = 5
DEFAULT_TIMEOUT_2 = 60

# Pipette 1 workflow addresses
ASPIRATE_ADDRESS = 2
DISPENSE_ADDRESS = 3
HOME_ADDRESS = 4
COMPLETION_ADDRESS = 1  # PC completion acknowledgment address

# Pipette 2 workflow addresses
ASPIRATE_ADDRESS_2 = 6
DISPENSE_ADDRESS_2 = 7
HOME_ADDRESS_2 = 8
COMPLETION_ADDRESS_2 = 5  # PC completion acknowledgment address