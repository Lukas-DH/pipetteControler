# Dual Pipette Control System

## Overview
Laboratory automation system controlling 2 INTEGRA VIAFLO Pipette II units via Modbus TCP protocol for robotic integration.

## System Architecture
- **Modbus TCP Server** (`server.py`) - Network interface for robot communication
- **Pipette Controller** (`pipette_controller.py`) - Direct serial communication with pipettes
- **Integration Script** (`integrate_pipette.py`) - Command-line interface
- **Configuration** (`config.py`) - System parameters

## Pipette Configuration

### Pipette 1
- **Port**: `/dev/tty.usbserial-FT3LK3ZO` (macOS)
- **Modbus Addresses**: Aspirate=2, Dispense=3, Home=4, Completion=1
- **Defaults**: Volume=5000, Dispense=1250, Speed=5

### Pipette 2
- **Port**: `/dev/tty.usbserial-FT3LK3Z1` (update this!)
- **Modbus Addresses**: Aspirate=6, Dispense=7, Home=8, Completion=5
- **Defaults**: Volume=5000, Dispense=1250, Speed=5

## Key Commands
- **Start Server**: `python server.py`
- **Test Pipette**: `python integrate_pipette.py aspirate --volume 1000 --port /dev/tty.usbserial-FT3LK3ZO`
- **Service**: `systemctl start pipette-server`

## Dependencies
- `pymodbus>=3.0.0`
- `pyserial>=3.5`

## Development Notes
- Both pipettes can operate independently
- Robot sends commands via Modbus TCP to trigger workflows
- Each pipette has unique addresses to avoid conflicts
- System automatically routes commands to correct serial port