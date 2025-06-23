#!/usr/bin/env python3
"""
Python Remote Control for INTEGRA Biosciences VIAFLO Pipette II
Based on the C# RemoteControl library protocol implementation.
"""

import serial
import struct
import time
import threading
from enum import IntEnum
from typing import Optional, Callable


class SetAction(IntEnum):
    """Available pipette actions"""
    NONE = 0
    ASPIRATE = 1
    DISPENSE = 2
    MIX = 3
    PURGE = 4
    BLOW_OUT = 5
    BLOW_IN = 6
    DISPENSE_WITH_NO_BLOW_OUT = 7
    HOME_PIPETTE = 8
    SPACE = 9
    HOME_SPACER = 10
    MIX_WITH_NO_BLOW_OUT = 11
    REL_MIX_ASPIRATE = 12
    REL_MIX_DISPENSE = 13


class MsgType(IntEnum):
    """Message types for communication"""
    GET_INFO = 0x01
    GET_ACTION_STATUS = 0x02
    GET_CALIBRATION_FACTOR = 0x03
    SET_CALIBRATION_FACTOR = 0x04
    SET_ACTION = 0x05
    EXIT_REMOTE_MODE = 0x06
    POWER_OFF = 0x07
    ABORT = 0x08
    SET_SCREEN = 0x09
    SET_BRIGHTNESS = 0x10
    GET_BATTERY_INFO = 0x11


class StatusCode(IntEnum):
    """Response status codes"""
    COMMAND_ACCEPTED = 0
    UNKNOWN_MESSAGE_TYPE = 1
    VALUE_OUT_OF_RANGE = 2
    HARDWARE_ERROR = 3
    COMMAND_NOT_ACCEPTED = 4


class ActionStatus(IntEnum):
    """Action status codes"""
    READY = 0
    WAIT_FOR_BLOWIN = 1
    WAIT_FOR_RUN_KEY = 2
    BUSY = 3
    PIPETTE_NOT_HOMED = 4
    USER_ABORT = 5


class PipetteController:
    """Remote control for VIAFLO Pipette II"""
    
    # Protocol constants
    STX = 0x02
    ETX = 0x03
    ESC = 0x1B
    
    def __init__(self, port_name: str, baudrate: int = 115200):
        """Initialize the pipette controller
        
        Args:
            port_name: Serial port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Communication speed (default 115200)
        """
        self.port_name = port_name
        self.baudrate = baudrate
        self.serial_port: Optional[serial.Serial] = None
        self.sequence_number = 1
        self.response_callback: Optional[Callable] = None
        self._timeout = 1.0
        self._retries = 3
        
    def connect(self) -> bool:
        """Connect to the pipette
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.serial_port = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                bytesize=8,
                parity=serial.PARITY_NONE,
                stopbits=1,
                timeout=self._timeout,
                write_timeout=0.5
            )
            print(f"Connected to pipette on {self.port_name}")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the pipette"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            print("Disconnected from pipette")
    
    def _build_checksum(self, data: bytes) -> int:
        """Calculate checksum for message"""
        checksum = sum(data) % 256
        return (256 - checksum) % 256
    
    def _escape_data(self, data: bytes) -> bytes:
        """Escape STX, ETX, and ESC characters in data"""
        escaped = bytearray()
        for byte in data:
            if byte in (self.STX, self.ETX, self.ESC):
                escaped.append(self.ESC)
            escaped.append(byte)
        return bytes(escaped)
    
    def _build_message(self, msg_type: int, data: bytes = b'') -> bytes:
        """Build a complete message frame"""
        # Increment sequence number
        if self.sequence_number > 65000:
            self.sequence_number = 1
        else:
            self.sequence_number += 1
        
        # Build message header (8 bytes + data)
        length = 8 + len(data)
        header = struct.pack('>HHBHHBB', 
            length,           # Length (2 bytes)
            0,                # Checksum placeholder (2 bytes) 
            self.sequence_number,  # Sequence number (2 bytes)
            0,                # Resend flag (1 byte)
            msg_type          # Message type (1 byte)
        )
        
        # Combine header and data
        message = header + data
        
        # Calculate and insert checksum
        checksum = self._build_checksum(message)
        message = message[:2] + struct.pack('B', checksum) + message[3:]
        
        # Escape special characters
        escaped_message = self._escape_data(message)
        
        # Add STX and ETX
        frame = bytes([self.STX]) + escaped_message + bytes([self.ETX])
        
        return frame
    
    def _send_message(self, msg_type: int, data: bytes = b'') -> bool:
        """Send a message to the pipette"""
        if not self.serial_port or not self.serial_port.is_open:
            print("Serial port not open")
            return False
        
        message = self._build_message(msg_type, data)
        
        try:
            # Clear input buffer
            self.serial_port.reset_input_buffer()
            
            # Send message
            self.serial_port.write(message)
            self.serial_port.flush()
            
            print(f"Sent message type {msg_type} (sequence {self.sequence_number})")
            return True
            
        except serial.SerialException as e:
            print(f"Failed to send message: {e}")
            return False
    
    def _wait_for_response(self, timeout: float = 2.0) -> Optional[tuple]:
        """Wait for and parse response from pipette"""
        if not self.serial_port or not self.serial_port.is_open:
            return None
        
        start_time = time.time()
        buffer = bytearray()
        
        while time.time() - start_time < timeout:
            if self.serial_port.in_waiting > 0:
                data = self.serial_port.read(self.serial_port.in_waiting)
                buffer.extend(data)
                
                # Look for complete message (STX...ETX)
                if self.STX in buffer and self.ETX in buffer:
                    stx_pos = buffer.find(self.STX)
                    etx_pos = buffer.find(self.ETX, stx_pos)
                    
                    if etx_pos > stx_pos:
                        # Extract message
                        raw_message = bytes(buffer[stx_pos+1:etx_pos])
                        
                        # Unescape message
                        message = self._unescape_data(raw_message)
                        
                        # Parse response
                        if len(message) >= 8:
                            length = struct.unpack('>H', message[0:2])[0]
                            checksum = message[2]
                            seq_num = struct.unpack('>H', message[3:5])[0]
                            msg_type = message[7]
                            
                            # Extract status code and any additional data
                            if len(message) > 8:
                                status_code = struct.unpack('>H', message[8:10])[0]
                                response_data = message[10:] if len(message) > 10 else b''
                                return (status_code, response_data, seq_num, msg_type)
                            else:
                                return (0, b'', seq_num, msg_type)
                        
                        break
            
            time.sleep(0.01)
        
        print("Response timeout")
        return None
    
    def _unescape_data(self, data: bytes) -> bytes:
        """Remove escape characters from data"""
        unescaped = bytearray()
        i = 0
        while i < len(data):
            if data[i] == self.ESC and i + 1 < len(data):
                i += 1  # Skip escape character
            unescaped.append(data[i])
            i += 1
        return bytes(unescaped)
    
    def get_action_status(self) -> Optional[tuple]:
        """Get current action status of the pipette"""
        if self._send_message(MsgType.GET_ACTION_STATUS):
            response = self._wait_for_response()
            if response:
                status_code, data, seq_num, msg_type = response
                if status_code == StatusCode.COMMAND_ACCEPTED and len(data) >= 4:
                    action_status = struct.unpack('>H', data[0:2])[0]
                    hardware_error = struct.unpack('>H', data[2:4])[0]
                    return (ActionStatus(action_status), hardware_error)
                else:
                    print(f"Command failed with status code: {status_code}")
            return None
    
    def purge(self, speed: int = 5, message: str = "Purging...") -> bool:
        """Execute purge command
        
        Args:
            speed: Purge speed (1-10, where 10 is fastest)
            message: Message to display on pipette (max 20 characters)
            
        Returns:
            True if command was accepted, False otherwise
        """
        # Ensure message is max 20 characters and pad with nulls
        display_msg = message[:20].ljust(20, '\0')
        
        # Build SetAction request data
        action_data = struct.pack('>BBHBBH20sH',
            SetAction.PURGE,    # Action type
            speed,              # Speed (1-10)
            0,                  # Volume (not used for purge)
            0,                  # Mix cycles (not used for purge) 
            0,                  # RUN confirmation (0 = no confirmation needed)
            0,                  # Reserved
            display_msg.encode('ascii', 'ignore'),  # Display message (20 bytes)
            0                   # Spacing (not used for purge)
        )
        
        print(f"Executing purge command (speed: {speed})")
        
        if self._send_message(MsgType.SET_ACTION, action_data):
            response = self._wait_for_response()
            if response:
                status_code, data, seq_num, msg_type = response
                if status_code == StatusCode.COMMAND_ACCEPTED:
                    print("Purge command accepted")
                    return True
                else:
                    print(f"Purge command failed with status code: {status_code}")
                    return False
        return False
    
    def get_info(self) -> Optional[dict]:
        """Get pipette information"""
        if self._send_message(MsgType.GET_INFO):
            response = self._wait_for_response()
            if response:
                status_code, data, seq_num, msg_type = response
                if status_code == StatusCode.COMMAND_ACCEPTED and len(data) >= 10:
                    fw_major = data[0]
                    fw_minor = data[1]
                    hw_version = data[3]
                    serial_num = struct.unpack('>I', data[4:8])[0]
                    model_type = struct.unpack('>H', data[8:10])[0]
                    
                    return {
                        'firmware_version': f"{fw_major}.{fw_minor}",
                        'hardware_version': f"{hw_version}.0",
                        'serial_number': serial_num,
                        'model_type': model_type
                    }
        return None


def main():
    """Main application"""
    # Configure your serial port here
    PORT_NAME = "COM3"  # Change this to your serial port (e.g., "/dev/ttyUSB0" on Linux)
    
    # Create controller instance
    controller = PipetteController(PORT_NAME)
    
    try:
        # Connect to pipette
        if not controller.connect():
            print("Failed to connect to pipette")
            return
        
        # Get pipette info
        print("\nGetting pipette information...")
        info = controller.get_info()
        if info:
            print(f"Firmware: {info['firmware_version']}")
            print(f"Hardware: {info['hardware_version']}")
            print(f"Serial: {info['serial_number']}")
            print(f"Model: {info['model_type']}")
        
        # Check status before purging
        print("\nChecking pipette status...")
        status = controller.get_action_status()
        if status:
            action_status, hw_error = status
            print(f"Action Status: {ActionStatus(action_status).name}")
            if hw_error != 0:
                print(f"Hardware Error: {hw_error}")
        
        # Execute purge command
        print("\nExecuting purge command...")
        success = controller.purge(speed=7, message="Python Purge")
        
        if success:
            print("Purge command sent successfully!")
            
            # Monitor status during purge
            print("Monitoring purge status...")
            for i in range(30):  # Monitor for up to 30 seconds
                time.sleep(1)
                status = controller.get_action_status()
                if status:
                    action_status, hw_error = status
                    print(f"Status: {ActionStatus(action_status).name}")
                    
                    if action_status == ActionStatus.READY:
                        print("Purge completed!")
                        break
                    elif action_status == ActionStatus.USER_ABORT:
                        print("Purge was aborted by user")
                        break
                else:
                    print("Failed to get status")
                    break
        else:
            print("Failed to execute purge command")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Disconnect
        controller.disconnect()


if __name__ == "__main__":
    main()