#!/usr/bin/env python3
"""
Modbus Status Reader
Read current values from all addresses on the Modbus server
"""

import argparse
from pymodbus.client import ModbusTcpClient

def read_coils(host, port, start_address=0, count=10):
    """Read coil status from Modbus server"""
    try:
        client = ModbusTcpClient(host, port=port)
        
        if not client.connect():
            print(f"❌ Failed to connect to {host}:{port}")
            return False
        
        print(f"📖 Reading {count} coils starting from address {start_address}...")
        print(f"Connected to Modbus server at {host}:{port}")
        print()
        
        # Read coils
        result = client.read_coils(address=start_address, count=count)
        
        if result.isError():
            print(f"❌ Error reading coils: {result}")
        else:
            print("Current Coil Status:")
            print("-------------------")
            for i, value in enumerate(result.bits[:count]):
                actual_address = start_address + i + 1  # Account for +1 offset
                status = "TRUE " if value else "FALSE"
                indicator = "🟢" if value else "⚫"
                print(f"Address {actual_address:2d}: {status} {indicator}")
            
            print()
            print("Legend: 🟢 = TRUE, ⚫ = FALSE")
            print("Note: Address 2 triggers pipette aspirate")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def monitor_mode(host, port, start_address=0, count=10, interval=2):
    """Continuously monitor coil status"""
    import time
    import os
    
    print(f"🔄 Monitoring mode - refreshing every {interval} seconds")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            # Clear screen (works on most terminals)
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("=== MODBUS STATUS MONITOR ===")
            print(f"Server: {host}:{port}")
            print(f"Time: {time.strftime('%H:%M:%S')}")
            print()
            
            read_coils(host, port, start_address, count)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")

def main():
    parser = argparse.ArgumentParser(description='Read Modbus server status')
    # Import config for defaults
    from config import MODBUS_HOST, MODBUS_PORT
    
    parser.add_argument('--host', type=str, default=MODBUS_HOST, help=f'Host (default: {MODBUS_HOST})')
    parser.add_argument('--port', type=int, default=MODBUS_PORT, help=f'Port (default: {MODBUS_PORT})')
    parser.add_argument('--start', type=int, default=0, help='Start address (default: 0)')
    parser.add_argument('--count', type=int, default=10, help='Number of addresses to read (default: 10)')
    parser.add_argument('--monitor', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=2, help='Monitor refresh interval in seconds (default: 2)')
    
    args = parser.parse_args()
    
    if args.monitor:
        monitor_mode(args.host, args.port, args.start, args.count, args.interval)
    else:
        success = read_coils(args.host, args.port, args.start, args.count)
        return 0 if success else 1

if __name__ == "__main__":
    exit(main())