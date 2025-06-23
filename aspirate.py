import serial

def parse_response(resp_bytes):
    if len(resp_bytes) < 9:
        print("Response too short!")
        return

    idx = 0
    stx = resp_bytes[idx]; idx += 1
    length = (resp_bytes[idx] << 8) + resp_bytes[idx+1]; idx += 2
    checksum = resp_bytes[idx]; idx += 1
    seq = (resp_bytes[idx] << 8) + resp_bytes[idx+1]; idx += 2
    resend_flag = resp_bytes[idx]; idx += 1
    msg_type = (resp_bytes[idx] << 8) + resp_bytes[idx+1]; idx += 2

    # Most responses will have at least a status code (2 bytes)
    if len(resp_bytes) > idx + 1:
        status_code = (resp_bytes[idx] << 8) + resp_bytes[idx+1]; idx += 2
    else:
        status_code = None

    data = resp_bytes[idx:-1] if len(resp_bytes) > idx+1 else b""
    etx = resp_bytes[-1]

    print(f"STX:         {stx:#04x}")
    print(f"Length:      {length}")
    print(f"Checksum:    {checksum:#04x}")
    print(f"Seq:         {seq}")
    print(f"Resend flag: {resend_flag}")
    print(f"Msg type:    {msg_type:#06x}")
    print(f"Status code: {status_code}")
    print(f"Data:        {data.hex() if data else '<none>'}")
    print(f"ETX:         {etx:#04x}")

    # Status code mapping
    status_meaning = {
        0x00: "Command accepted (OK)",
        0x01: "Unknown message type (protocol error)",
        0x02: "Value/parameter out of range or wrong number of bytes",
        0x03: "Hardware error - check pipette status",
        0x04: "Command not accepted - action or state invalid",
        0x64: "Unknown/custom status code (0x64) - check protocol documentation",
        # Add more codes here as needed
    }

    desc = status_meaning.get(status_code, None)
    if desc is not None:
        print(f"Status desc: {desc}")
    else:
        print(f"Status desc: Unknown code (dec: {status_code}, hex: {status_code:#04x}), see pipette manual.")



def send_aspirate_command(port='/dev/tty.usbserial-FT3LK3ZO'):
    # ... rest of code ...
    # The message as bytes (hex values)
    cmd = bytes([
        0x02, 0x00, 0x24, 0x64, 0x00, 0x00, 0x00, 0x00, 0x05, 0x04, 0x05, 0x00, 0x00, 0x00, 0x00,
        0x49, 0x6E, 0x74, 0x65, 0x67, 0x72, 0x61, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20,
        0x20, 0x20, 0x20, 0x20, 0x20, 0x00, 0x00, 0x03
    ])
    with serial.Serial(port, baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=1) as ser:
        ser.write(cmd)
        # read response
        response = ser.read(64)
        print("Response:", response.hex())
        parse_response(response)

# Run this script on a PC or Raspberry Pi with USB serial connected to the pipette.
send_aspirate_command()


def parse_response(resp_bytes):
    if len(resp_bytes) < 9:
        print("Response too short!")
        return

    idx = 0
    stx = resp_bytes[idx]; idx += 1
    length = (resp_bytes[idx] << 8) + resp_bytes[idx+1]; idx += 2
    checksum = resp_bytes[idx]; idx += 1
    seq = (resp_bytes[idx] << 8) + resp_bytes[idx+1]; idx += 2
    resend_flag = resp_bytes[idx]; idx += 1
    msg_type = (resp_bytes[idx] << 8) + resp_bytes[idx+1]; idx += 2

    # Most responses will have at least a status code (2 bytes)
    if len(resp_bytes) > idx + 1:
        status_code = (resp_bytes[idx] << 8) + resp_bytes[idx+1]; idx += 2
    else:
        status_code = None

    data = resp_bytes[idx:-1] if len(resp_bytes) > idx+1 else b""
    etx = resp_bytes[-1]

    print(f"STX:         {stx:#04x}")
    print(f"Length:      {length}")
    print(f"Checksum:    {checksum:#04x}")
    print(f"Seq:         {seq}")
    print(f"Resend flag: {resend_flag}")
    print(f"Msg type:    {msg_type:#06x}")
    print(f"Status code: {status_code}")
    print(f"Data:        {data.hex() if data else '<none>'}")
    print(f"ETX:         {etx:#04x}")

    # Status code mapping
    status_meaning = {
        0x00: "Command accepted (OK)",
        0x01: "Unknown message type (protocol error)",
        0x02: "Value/parameter out of range or wrong number of bytes",
        0x03: "Hardware error - check pipette status",
        0x04: "Command not accepted - action or state invalid",
        0x64: "Unknown/custom status code (0x64) - check protocol documentation",
        # Add more codes here as needed
    }

    desc = status_meaning.get(status_code, None)
    if desc is not None:
        print(f"Status desc: {desc}")
    else:
        print(f"Status desc: Unknown code (dec: {status_code}, hex: {status_code:#04x}), see pipette manual.")
