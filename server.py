from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSparseDataBlock, ModbusSlaveContext, ModbusServerContext
import logging
import subprocess
import threading
import time

# Disable verbose logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.WARNING)

class PipetteWorkflow:
    """Base class for pipette workflow commands"""
    def __init__(self, name, address, command, args):
        self.name = name
        self.address = address  # Command address (2, 3, 4, etc.)
        self.command = command  # Pipette command
        self.args = args       # Command arguments
        self.emoji = "🔬"       # Default emoji
    
    def get_description(self):
        return f"{self.emoji} {self.name}"

class PipetteWorkflowDataBlock(ModbusSparseDataBlock):
    def __init__(self, values):
        super().__init__(values)
        self.pipette_busy = False
        self.workflow_state = "IDLE"  # IDLE, ACKNOWLEDGED, RUNNING, COMPLETED
        self.current_workflow = None
        
        # Import config for workflow parameters
        from config import (DEFAULT_ASPIRATE_VOLUME, DEFAULT_DISPENSE_VOLUME, DEFAULT_SPEED,
                           ASPIRATE_ADDRESS, DISPENSE_ADDRESS, HOME_ADDRESS)
        
        # Define workflow commands
        self.workflows = {
            ASPIRATE_ADDRESS: PipetteWorkflow(
                name="Aspirate (Fill Pipette)",
                address=ASPIRATE_ADDRESS,
                command="aspirate",
                args=["--volume", str(DEFAULT_ASPIRATE_VOLUME), "--speed", str(DEFAULT_SPEED)]
            ),
            DISPENSE_ADDRESS: PipetteWorkflow(
                name="Dispense (Drop in Dish)",
                address=DISPENSE_ADDRESS, 
                command="dispense",
                args=["--volume", str(DEFAULT_DISPENSE_VOLUME), "--speed", str(DEFAULT_SPEED)]
            ),
            HOME_ADDRESS: PipetteWorkflow(
                name="Home (Return to Rack)",
                address=HOME_ADDRESS,
                command="home", 
                args=["--speed", str(DEFAULT_SPEED)]
            )
        }
        
        # Set emojis for different workflows
        self.workflows[ASPIRATE_ADDRESS].emoji = "💧"  # Aspirate
        self.workflows[DISPENSE_ADDRESS].emoji = "🥽"  # Dispense 
        self.workflows[HOME_ADDRESS].emoji = "🏠"  # Home
        
    def setValues(self, address, values):
        print(f"Received at address {address}: {values}")
        
        # Handle workflow command addresses (2, 3, 4, etc.)
        if address in self.workflows and values:
            workflow = self.workflows[address]
            if values[0] == True:
                self.handle_robot_request(workflow)
            elif values[0] == False:
                self.handle_robot_acknowledge_completion(workflow)
        
        super().setValues(address, values)
    
    def handle_robot_request(self, workflow):
        """Handle robot setting command address = 1 (request action)"""
        if self.workflow_state != "IDLE":
            print(f"⚠️  Workflow not in IDLE state, ignoring {workflow.name} request")
            return
        
        print(f"🤖 Robot requests: {workflow.get_description()} (Address{workflow.address} = 1)")
        print("💻 PC acknowledging request...")
        
        # Set Address1 = 1 to acknowledge
        self.setValues(1, [True])
        self.workflow_state = "ACKNOWLEDGED"
        self.current_workflow = workflow
        
        print("✅ PC set Address1 = 1 (acknowledged)")
        print(f"{workflow.emoji} Starting {workflow.command} process...")
        
        # Start workflow in separate thread
        self.execute_workflow(workflow)
    
    def handle_robot_acknowledge_completion(self, workflow):
        """Handle robot setting command address = 0 (acknowledges completion)"""
        if self.workflow_state != "COMPLETED" or self.current_workflow != workflow:
            print(f"⚠️  Not waiting for {workflow.name} acknowledgment, ignoring")
            return
        
        print(f"🤖 Robot acknowledges {workflow.name} completion (Address{workflow.address} = 0)")
        print("🔄 Returning to IDLE state")
        
        self.workflow_state = "IDLE"
        self.current_workflow = None
        print("✅ Workflow cycle completed - ready for next cycle")
    
    def execute_workflow(self, workflow):
        """Execute the specified workflow command"""
        if self.pipette_busy:
            print(f"⚠️  Pipette is busy, cannot start {workflow.name}")
            return
            
        def run_command():
            try:
                self.pipette_busy = True
                self.workflow_state = "RUNNING"
                print(f"🚀 Executing {workflow.name}...")
                
                # Build command arguments
                cmd_args = ['python', 'integrate_pipette.py', workflow.command] + workflow.args
                print(f"Command: {' '.join(cmd_args)}")
                
                # Run the integrate_pipette.py script
                result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"✅ {workflow.name} completed successfully")
                    print("💻 PC signaling completion...")
                    
                    # Set Address1 = 0 to signal completion
                    self.setValues(1, [False])
                    self.workflow_state = "COMPLETED"
                    print("✅ PC set Address1 = 0 (completion signal)")
                    print(f"⏳ Waiting for robot to acknowledge (Address{workflow.address} = 0)...")
                    
                else:
                    print(f"❌ {workflow.name} failed")
                    print(f"Error: {result.stderr}")
                    self.reset_workflow("error")
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ {workflow.name} command timed out")
                self.reset_workflow("timeout")
            except Exception as e:
                print(f"❌ Error running {workflow.name}: {e}")
                self.reset_workflow("exception")
            finally:
                self.pipette_busy = False
        
        # Run in separate thread to avoid blocking Modbus server
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def reset_workflow(self, reason):
        """Reset workflow state due to error"""
        self.setValues(1, [False])
        self.workflow_state = "IDLE"
        self.current_workflow = None
        print(f"🔄 Workflow reset due to {reason}")
    
    def get_workflow_status(self):
        """Get current workflow status for debugging"""
        status = {
            'state': self.workflow_state,
            'address1': self.getValues(1, 1)[0] if self.getValues(1, 1) else False,
            'pipette_busy': self.pipette_busy,
            'current_workflow': self.current_workflow.name if self.current_workflow else None
        }
        
        # Add status for all workflow addresses
        for addr, workflow in self.workflows.items():
            status[f'address{addr}'] = self.getValues(addr, 1)[0] if self.getValues(addr, 1) else False
        
        return status

# Use our custom PipetteWorkflowDataBlock with multiple addresses
block = PipetteWorkflowDataBlock({i: 0 for i in range(100)})
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

# Start the Modbus server 
from config import MODBUS_PORT as config_port
print(f"Starting Modbus TCP server on port {config_port}...")
print("🔬 Pipette-Robot Workflow Integration:")
print()
print("AVAILABLE WORKFLOWS:")
for addr, workflow in block.workflows.items():
    print(f"   Address{addr}: {workflow.get_description()}")
print()
print("WORKFLOW CYCLE (Address1 = completion acknowledgment):")
print("   1. Robot sets Address[X] = 1 (request action)")
print("   2. PC sets Address1 = 1 (acknowledge)")
print("   3. PC runs pipette command")
print("   4. PC sets Address1 = 0 (completion signal)")
print("   5. Robot sets Address[X] = 0 (acknowledge completion)")
print("   6. Return to idle state")
print()
print("TESTING COMMANDS:")
print("   python simulator.py --true --address 1   # Aspirate")
print("   python simulator.py --true --address 2   # Dispense") 
print("   python simulator.py --true --address 3   # Home")
print("   python status_reader.py --monitor        # Monitor state")
print()

from config import MODBUS_PORT

try:
    StartTcpServer(context, identity=identity, address=("0.0.0.0", MODBUS_PORT))
except KeyboardInterrupt:
    print("\n🛑 Server shutdown requested")
except Exception as e:
    print(f"❌ Server error: {e}")
finally:
    print("👋 Modbus server stopped")