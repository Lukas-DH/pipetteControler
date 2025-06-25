#!/usr/bin/env python3
"""
Simple Modbus Simulator
Send true/false signals to test pipette integration
"""

import argparse
from pymodbus.client import ModbusTcpClient

def send_signal(host, port, address, value):
    """Send a boolean signal to the Modbus server"""
    try:
        client = ModbusTcpClient(host, port=port)
        
        if not client.connect():
            print(f"❌ Failed to connect to {host}:{port}")
            return False
        
        print(f"📡 Sending {value} to address {address}...")
        
        result = client.write_coil(address, value)
        
        if result.isError():
            print(f"❌ Error: {result}")
            success = False
        else:
            status = "TRUE" if value else "FALSE"
            print(f"✅ Successfully sent {status} to address {address}")
            success = True
        
        client.close()
        return success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Send signals to Modbus server')
    parser.add_argument('--true', action='store_true', help='Send TRUE signal')
    parser.add_argument('--false', action='store_true', help='Send FALSE signal')
    parser.add_argument('--address', type=int, default=2, help='Address (default: 2)')
    # Import config for defaults
    from config import MODBUS_HOST, MODBUS_PORT
    
    parser.add_argument('--host', type=str, default=MODBUS_HOST, help=f'Host (default: {MODBUS_HOST})')
    parser.add_argument('--port', type=int, default=MODBUS_PORT, help=f'Port (default: {MODBUS_PORT})')
    
    args = parser.parse_args()
    
    if args.true and args.false:
        print("❌ Cannot specify both --true and --false")
        return 1
    
    if not args.true and not args.false:
        print("❌ Must specify either --true or --false")
        return 1
    
    value = True if args.true else False
    
    success = send_signal(args.host, args.port, args.address, value)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())