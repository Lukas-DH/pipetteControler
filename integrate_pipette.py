#!/usr/bin/env python3
"""
Command-line Pipette Controller
Control INTEGRA Biosciences VIAFLO Pipette II with command-line arguments
"""

import argparse
import sys
import time
from pipette_controller import PipetteController, SetAction, ActionStatus, StatusCode


def get_action_type(action_name: str) -> SetAction:
    """Convert action name to SetAction enum"""
    action_map = {
        'aspirate': SetAction.ASPIRATE,
        'dispense': SetAction.DISPENSE,
        'mix': SetAction.MIX,
        'purge': SetAction.PURGE,
        'blow-out': SetAction.BLOW_OUT,
        'blow-in': SetAction.BLOW_IN,
        'dispense-no-blowout': SetAction.DISPENSE_WITH_NO_BLOW_OUT,
        'home': SetAction.HOME_PIPETTE,
        'space': SetAction.SPACE,
        'home-spacer': SetAction.HOME_SPACER,
        'mix-no-blowout': SetAction.MIX_WITH_NO_BLOW_OUT,
        'rel-mix-aspirate': SetAction.REL_MIX_ASPIRATE,
        'rel-mix-dispense': SetAction.REL_MIX_DISPENSE
    }
    return action_map.get(action_name.lower())


def execute_action(controller: PipetteController, action_type: SetAction, 
                  speed: int, volume: int, mix_cycles: int, message: str, 
                  run_confirmation: bool, monitor: bool, timeout: int) -> bool:
    """Execute a pipette action with specified parameters"""
    
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
    
    print(f"Executing {action_type.name}:")
    print(f"  Speed: {speed}")
    print(f"  Volume: {volume}")
    if mix_cycles > 0:
        print(f"  Mix cycles: {mix_cycles}")
    if run_confirmation:
        print(f"  RUN confirmation: Required")
    if message:
        print(f"  Message: '{message}'")
    
    # Send command
    if controller._send_message(5, bytes(action_data)):  # MsgType.SET_ACTION = 5
        response = controller._wait_for_response()
        if response:
            status_code, data, seq_num, msg_type = response
            if status_code == StatusCode.COMMAND_ACCEPTED:
                print(f"✓ {action_type.name} command accepted")
                
                if monitor:
                    return monitor_action(controller, timeout)
                return True
            else:
                status_descriptions = {
                    0: "Command accepted",
                    1: "Unknown message type",
                    2: "Value/parameter out of range",
                    3: "Hardware error",
                    4: "Command not accepted"
                }
                desc = status_descriptions.get(status_code, f"Unknown status code: {status_code}")
                print(f"✗ {action_type.name} command failed: {desc} (code: {status_code})")
                return False
        else:
            print(f"✗ No response received for {action_type.name} command")
    else:
        print(f"✗ Failed to send {action_type.name} command")
    
    return False


def monitor_action(controller: PipetteController, timeout: int = 30) -> bool:
    """Monitor action progress until completion or timeout following manual process"""
    print(f"Monitoring action progress (timeout: {timeout}s)...")
    
    start_time = time.time()
    check_interval = 0.5  # Check status every 500ms for more responsive monitoring
    
    while time.time() - start_time < timeout:
        # Get action status as per manual process
        if controller._send_message(2):  # MsgType.GET_ACTION_STATUS = 2
            response = controller._wait_for_response(timeout=1.0)
            if response:
                status_code, data, seq_num, msg_type = response
                
                if status_code == StatusCode.COMMAND_ACCEPTED and len(data) >= 4:
                    action_status = (data[0] << 8) | data[1]
                    hardware_error = (data[2] << 8) | data[3]
                    
                    try:
                        status_name = ActionStatus(action_status).name
                    except ValueError:
                        status_name = f"UNKNOWN({action_status})"
                    
                    elapsed = int(time.time() - start_time)
                    print(f"  [{elapsed:2d}s] Status: {status_name}")
                    
                    if hardware_error != 0:
                        print(f"  Hardware Error: {hardware_error}")
                    
                    # Check action status as per manual
                    if action_status == ActionStatus.READY:
                        print("✓ Action completed successfully!")
                        return True
                    elif action_status == ActionStatus.USER_ABORT:
                        print("✗ Action aborted by user")
                        return False
                    elif action_status == ActionStatus.WAIT_FOR_RUN_KEY:
                        print("⚠ Waiting for RUN key press on pipette...")
                    elif action_status == ActionStatus.BUSY:
                        # Continue monitoring as per manual - pipette is executing
                        pass
                    elif action_status == ActionStatus.PIPETTE_NOT_HOMED:
                        print("⚠ Pipette not homed - action may fail")
                    elif action_status == ActionStatus.WAIT_FOR_BLOWIN:
                        print("⚠ Waiting for blow-in before next aspirate")
                        return True  # Action completed, but needs blow-in for next cycle
                else:
                    print(f"  Status check failed with code: {status_code}")
                    # Don't immediately fail - try again
            else:
                print(f"  No response to status check")
                # Don't immediately fail - try again
        else:
            print(f"  Failed to send status request")
        
        time.sleep(check_interval)
    
    print("⚠ Monitoring timeout reached")
    return False


def get_status(controller: PipetteController) -> bool:
    """Get and display current pipette status"""
    if controller._send_message(2):  # MsgType.GET_ACTION_STATUS = 2
        response = controller._wait_for_response(timeout=2.0)
        if response:
            status_code, data, seq_num, msg_type = response
            
            if status_code == StatusCode.COMMAND_ACCEPTED and len(data) >= 4:
                action_status = (data[0] << 8) | data[1]
                hardware_error = (data[2] << 8) | data[3]
                
                try:
                    status_name = ActionStatus(action_status).name
                except ValueError:
                    status_name = f"UNKNOWN({action_status})"
                
                print(f"Pipette Status: {status_name}")
                if hardware_error != 0:
                    print(f"Hardware Error: {hardware_error}")
                return True
            else:
                print(f"Status command failed with code: {status_code}")
                return False
        else:
            print("No response to status request")
            return False
    else:
        print("Failed to send status request")
        return False


def get_info(controller: PipetteController) -> bool:
    """Get and display pipette information"""
    info = controller.get_info()
    if info:
        print("Pipette Information:")
        print(f"  Firmware: {info['firmware_version']}")
        print(f"  Hardware: {info['hardware_version']}")
        print(f"  Serial: {info['serial_number']}")
        print(f"  Model: {info['model_type']}")
        return True
    else:
        print("Failed to get pipette information")
        return False


def main():
    """Main command-line application"""
    parser = argparse.ArgumentParser(
        description='Command-line controller for INTEGRA VIAFLO Pipette II',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s aspirate --volume 100 --speed 5
  %(prog)s dispense --volume 50 --speed 8 --message "Test"
  %(prog)s mix --volume 200 --mix-cycles 5 --speed 6
  %(prog)s purge --speed 7
  %(prog)s home
  %(prog)s --info
  %(prog)s --status
        """
    )
    
    # Connection arguments
    # Import config for default port
    from config import PIPETTE_PORT
    
    parser.add_argument('--port', type=str, default=PIPETTE_PORT,
                       help=f'Serial port (default: {PIPETTE_PORT})')
    
    # Information commands
    parser.add_argument('--info', action='store_true',
                       help='Get pipette information')
    parser.add_argument('--status', action='store_true',
                       help='Get pipette status')
    
    # Action command
    parser.add_argument('action', nargs='?', 
                       choices=['aspirate', 'dispense', 'mix', 'purge', 'blow-out', 'blow-in',
                               'dispense-no-blowout', 'home', 'space', 'home-spacer',
                               'mix-no-blowout', 'rel-mix-aspirate', 'rel-mix-dispense'],
                       help='Action to perform')
    
    # Action parameters
    parser.add_argument('--speed', type=int, default=5, choices=range(1, 11),
                       help='Speed (1-10, default: 5)')
    parser.add_argument('--volume', type=int, default=100,
                       help='Volume in pipette units (default: 100)')
    parser.add_argument('--mix-cycles', type=int, default=3, choices=range(1, 31),
                       help='Mix cycles for mix actions (1-30, default: 3)')
    parser.add_argument('--message', type=str, default='',
                       help='Display message on pipette (max 20 characters)')
    parser.add_argument('--run-confirm', action='store_true',
                       help='Require RUN key confirmation before execution')
    
    # Monitoring options
    parser.add_argument('--no-monitor', action='store_true',
                       help='Do not monitor action progress')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Monitoring timeout in seconds (default: 30)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.info and not args.status and not args.action:
        parser.error("Must specify an action or use --info/--status")
    
    if args.action and args.action in ['aspirate', 'dispense', 'mix', 'dispense-no-blowout', 
                                      'mix-no-blowout', 'rel-mix-aspirate', 'rel-mix-dispense']:
        if args.volume <= 0:
            parser.error("Volume must be greater than 0 for volume-based actions")
    
    # Create controller
    controller = PipetteController(args.port)
    
    try:
        # Connect to pipette
        print(f"Connecting to pipette on {args.port}...")
        if not controller.connect():
            print("✗ Failed to connect to pipette")
            return 1
        
        success = True
        
        # Handle info command
        if args.info:
            success = get_info(controller)
        
        # Handle status command  
        elif args.status:
            success = get_status(controller)
        
        # Handle action command
        elif args.action:
            action_type = get_action_type(args.action)
            if action_type is None:
                print(f"✗ Unknown action: {args.action}")
                return 1
            
            # Validate volume for volume-based actions
            volume_actions = [SetAction.ASPIRATE, SetAction.DISPENSE, SetAction.MIX,
                            SetAction.DISPENSE_WITH_NO_BLOW_OUT, SetAction.MIX_WITH_NO_BLOW_OUT,
                            SetAction.REL_MIX_ASPIRATE, SetAction.REL_MIX_DISPENSE]
            
            volume = args.volume if action_type in volume_actions else 0
            mix_cycles = args.mix_cycles if action_type in [SetAction.MIX, SetAction.MIX_WITH_NO_BLOW_OUT] else 0
            
            success = execute_action(
                controller=controller,
                action_type=action_type,
                speed=args.speed,
                volume=volume,
                mix_cycles=mix_cycles,
                message=args.message,
                run_confirmation=args.run_confirm,
                monitor=not args.no_monitor,
                timeout=args.timeout
            )
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\n✗ Operation cancelled by user")
        return 1
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1
    
    finally:
        controller.disconnect()


if __name__ == "__main__":
    sys.exit(main())