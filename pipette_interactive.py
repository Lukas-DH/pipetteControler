#!/usr/bin/env python3
"""
Interactive Pipette Controller
Control INTEGRA Biosciences VIAFLO Pipette II with command-line interface
"""

import sys
import time
from pipette_controller import PipetteController, SetAction, ActionStatus, StatusCode


class InteractivePipetteController:
    """Interactive command-line interface for pipette control"""
    
    def __init__(self, port_name: str):
        self.controller = PipetteController(port_name)
        self.connected = False
        
    def connect(self):
        """Connect to the pipette"""
        if self.controller.connect():
            self.connected = True
            print("✓ Connected successfully!")
            
            # Get and display pipette info
            info = self.controller.get_info()
            if info:
                print(f"Pipette Info:")
                print(f"  Firmware: {info['firmware_version']}")
                print(f"  Hardware: {info['hardware_version']}")
                print(f"  Serial: {info['serial_number']}")
                print(f"  Model: {info['model_type']}")
            return True
        else:
            print("✗ Failed to connect")
            return False
    
    def disconnect(self):
        """Disconnect from pipette"""
        if self.connected:
            self.controller.disconnect()
            self.connected = False
    
    def get_status(self):
        """Get and display current pipette status"""
        if not self.connected:
            print("Not connected to pipette")
            return
        
        status = self.controller.get_action_status()
        if status:
            action_status, hw_error = status
            print(f"Status: {ActionStatus(action_status).name}")
            if hw_error != 0:
                print(f"Hardware Error: {hw_error}")
        else:
            print("Failed to get status")
    
    def execute_action(self, action_type: SetAction, speed: int = 5, volume: int = 0, 
                      mix_cycles: int = 0, message: str = "", run_confirmation: bool = False):
        """Execute a pipette action with specified parameters"""
        if not self.connected:
            print("Not connected to pipette")
            return False
        
        # Build action data
        display_msg = message[:20].ljust(20, '\0') if message else f"{action_type.name}...".ljust(20, '\0')
        display_bytes = display_msg.encode('ascii', 'ignore')[:20]
        
        action_data = bytearray()
        action_data.append(action_type)           # Action type (1 byte)
        action_data.append(speed)                 # Speed (1 byte)
        action_data.append(volume >> 8)           # Volume high byte
        action_data.append(volume & 0xFF)         # Volume low byte
        action_data.append(mix_cycles)            # Mix cycles (1 byte)
        action_data.append(1 if run_confirmation else 0)  # RUN confirmation (1 byte)
        action_data.extend(display_bytes[:20].ljust(20, b'\0'))  # Message (20 bytes)
        action_data.append(0)                     # Spacing high byte
        action_data.append(0)                     # Spacing low byte
        
        print(f"Executing {action_type.name} (speed: {speed}, volume: {volume}, mix_cycles: {mix_cycles})")
        
        if self.controller._send_message(5, bytes(action_data)):  # MsgType.SET_ACTION = 5
            response = self.controller._wait_for_response()
            if response:
                status_code, data, seq_num, msg_type = response
                if status_code == StatusCode.COMMAND_ACCEPTED:
                    print(f"✓ {action_type.name} command accepted")
                    return True
                else:
                    print(f"✗ {action_type.name} command failed with status code: {status_code}")
                    return False
        return False
    
    def monitor_action(self, timeout: int = 30):
        """Monitor action progress until completion or timeout"""
        print("Monitoring action progress...")
        for i in range(timeout):
            time.sleep(1)
            status = self.controller.get_action_status()
            if status:
                action_status, hw_error = status
                status_name = ActionStatus(action_status).name
                print(f"  [{i+1:2d}s] Status: {status_name}")
                
                if action_status == ActionStatus.READY:
                    print("✓ Action completed!")
                    return True
                elif action_status == ActionStatus.USER_ABORT:
                    print("✗ Action aborted by user")
                    return False
                elif action_status == ActionStatus.WAIT_FOR_RUN_KEY:
                    print("⚠ Waiting for RUN key press on pipette")
            else:
                print("Failed to get status")
                break
        
        print("⚠ Monitoring timeout reached")
        return False
    
    def aspirate(self, speed: int = 5, volume: int = 100, message: str = ""):
        """Aspirate liquid"""
        if self.execute_action(SetAction.ASPIRATE, speed, volume, 0, message):
            return self.monitor_action()
        return False
    
    def dispense(self, speed: int = 5, volume: int = 100, message: str = ""):
        """Dispense liquid"""
        if self.execute_action(SetAction.DISPENSE, speed, volume, 0, message):
            return self.monitor_action()
        return False
    
    def mix(self, speed: int = 5, volume: int = 100, mix_cycles: int = 3, message: str = ""):
        """Mix liquid"""
        if self.execute_action(SetAction.MIX, speed, volume, mix_cycles, message):
            return self.monitor_action()
        return False
    
    def purge(self, speed: int = 5, message: str = ""):
        """Purge pipette"""
        if self.execute_action(SetAction.PURGE, speed, 0, 0, message):
            return self.monitor_action()
        return False
    
    def blow_out(self, speed: int = 5, message: str = ""):
        """Blow out"""
        if self.execute_action(SetAction.BLOW_OUT, speed, 0, 0, message):
            return self.monitor_action()
        return False
    
    def blow_in(self, speed: int = 5, message: str = ""):
        """Blow in"""
        if self.execute_action(SetAction.BLOW_IN, speed, 0, 0, message):
            return self.monitor_action()
        return False
    
    def home(self, message: str = ""):
        """Home pipette"""
        if self.execute_action(SetAction.HOME_PIPETTE, 5, 0, 0, message):
            return self.monitor_action()
        return False


def get_int_input(prompt: str, default: int = None, min_val: int = None, max_val: int = None) -> int:
    """Get integer input with validation"""
    while True:
        try:
            if default is not None:
                value = input(f"{prompt} (default {default}): ").strip()
                if not value:
                    return default
                value = int(value)
            else:
                value = int(input(f"{prompt}: "))
            
            if min_val is not None and value < min_val:
                print(f"Value must be >= {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be <= {max_val}")
                continue
            
            return value
        except ValueError:
            print("Please enter a valid number")


def main():
    """Main interactive application"""
    print("=== Interactive Pipette Controller ===")
    print("INTEGRA Biosciences VIAFLO Pipette II Remote Control")
    print()
    
    # Get port name
    port_name = input("Enter serial port (default: /dev/tty.usbserial-FT3LK3ZO): ").strip()
    if not port_name:
        port_name = "/dev/tty.usbserial-FT3LK3ZO"
    
    # Create controller
    pipette = InteractivePipetteController(port_name)
    
    try:
        # Connect
        print(f"\nConnecting to {port_name}...")
        if not pipette.connect():
            return
        
        print("\nCommands available:")
        print("  1. Aspirate    2. Dispense    3. Mix")
        print("  4. Purge       5. Blow Out    6. Blow In")
        print("  7. Home        8. Status      9. Quit")
        print()
        
        while True:
            try:
                choice = input("Enter command (1-9): ").strip()
                
                if choice == '1':  # Aspirate
                    print("\n--- ASPIRATE ---")
                    speed = get_int_input("Speed (1-10)", 5, 1, 10)
                    volume = get_int_input("Volume", 100, 1, 5000)
                    message = input("Display message (optional): ").strip()
                    pipette.aspirate(speed, volume, message)
                
                elif choice == '2':  # Dispense
                    print("\n--- DISPENSE ---")
                    speed = get_int_input("Speed (1-10)", 5, 1, 10)
                    volume = get_int_input("Volume", 100, 1, 5000)
                    message = input("Display message (optional): ").strip()
                    pipette.dispense(speed, volume, message)
                
                elif choice == '3':  # Mix
                    print("\n--- MIX ---")
                    speed = get_int_input("Speed (1-10)", 5, 1, 10)
                    volume = get_int_input("Volume", 100, 1, 5000)
                    mix_cycles = get_int_input("Mix cycles (1-30)", 3, 1, 30)
                    message = input("Display message (optional): ").strip()
                    pipette.mix(speed, volume, mix_cycles, message)
                
                elif choice == '4':  # Purge
                    print("\n--- PURGE ---")
                    speed = get_int_input("Speed (1-10)", 5, 1, 10)
                    message = input("Display message (optional): ").strip()
                    pipette.purge(speed, message)
                
                elif choice == '5':  # Blow Out
                    print("\n--- BLOW OUT ---")
                    speed = get_int_input("Speed (1-10)", 5, 1, 10)
                    message = input("Display message (optional): ").strip()
                    pipette.blow_out(speed, message)
                
                elif choice == '6':  # Blow In
                    print("\n--- BLOW IN ---")
                    speed = get_int_input("Speed (1-10)", 5, 1, 10)
                    message = input("Display message (optional): ").strip()
                    pipette.blow_in(speed, message)
                
                elif choice == '7':  # Home
                    print("\n--- HOME PIPETTE ---")
                    message = input("Display message (optional): ").strip()
                    pipette.home(message)
                
                elif choice == '8':  # Status
                    print("\n--- PIPETTE STATUS ---")
                    pipette.get_status()
                
                elif choice == '9':  # Quit
                    break
                
                else:
                    print("Invalid choice. Please enter 1-9.")
                
                print()
                
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        pipette.disconnect()
        print("Disconnected. Goodbye!")


if __name__ == "__main__":
    main()