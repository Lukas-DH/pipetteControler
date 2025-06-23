from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSparseDataBlock, ModbusSlaveContext, ModbusServerContext
import logging

# Disable verbose logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.WARNING)

class PrintingDataBlock(ModbusSparseDataBlock):
    def setValues(self, address, values):
        print(f"Received at address {address}: {values}")
        super().setValues(address, values)

# Use our custom DataBlock with multiple addresses
block = PrintingDataBlock({i: 0 for i in range(100)})
store = ModbusSlaveContext(
    di=block, co=block, hr=block, ir=block
)
context = ModbusServerContext(slaves=store, single=True)

identity = ModbusDeviceIdentification()
identity.VendorName = 'YourCompany'
identity.ProductCode = 'PYMODBUS'
identity.VendorUrl = 'http://github.com/riptideio/pymodbus/'
identity.ProductName = 'Pymodbus Server'
identity.ModelName = 'Pymodbus Server'
identity.MajorMinorRevision = '1.0'

# Start the Modbus server (default port is 502; use 1502 if not root)
print("Starting Modbus TCP server on port 1502...")
StartTcpServer(context, identity=identity, address=("0.0.0.0", 502))