#!/usr/bin/env python3
"""
Configuration file for pipette integration system
Edit these values for your specific setup
"""

# Serial port configuration
# Common ports:
#   macOS: "/dev/tty.usbserial-FT3LK3ZO" 
#   Linux: "/dev/ttyUSB0"
#   Windows: "COM3"
PIPETTE_PORT = "/dev/tty.usbserial-FT3LK3ZO"

# Modbus server configuration
MODBUS_HOST = "localhost"
MODBUS_PORT = 502

# Pipette default parameters
DEFAULT_ASPIRATE_VOLUME = 5000
DEFAULT_DISPENSE_VOLUME = 1250
DEFAULT_SPEED = 5
DEFAULT_TIMEOUT = 60

# Workflow addresses
ASPIRATE_ADDRESS = 2
DISPENSE_ADDRESS = 3
HOME_ADDRESS = 4
COMPLETION_ADDRESS = 1  # PC completion acknowledgment address