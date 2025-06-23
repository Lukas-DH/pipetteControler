#!/usr/bin/env python3
import argparse
from pymodbus.client import ModbusTcpClient

def main():
    parser = argparse.ArgumentParser(description='Set coil value on Modbus server')
    parser.add_argument('--value', type=str, choices=['true', 'false'], required=True,
                        help='Value to set (true or false)')
    parser.add_argument('--address', type=int, default=2,
                        help='Coil address (default: 2)')
    parser.add_argument('--host', type=str, default='localhost',
                        help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=502,
                        help='Server port (default: 502)')
    
    args = parser.parse_args()
    
    # Convert string to boolean
    value = args.value.lower() == 'true'
    
    # Connect to server
    client = ModbusTcpClient(args.host, port=args.port)
    
    if not client.connect():
        print(f"Failed to connect to {args.host}:{args.port}")
        return
    
    # Write coil value
    result = client.write_coil(args.address, value)
    
    if result.isError():
        print(f"Error writing to address {args.address}: {result}")
    else:
        print(f"Successfully set address {args.address} to {value}")
    
    client.close()

if __name__ == '__main__':
    main()