import sys
import base64
import json
import socket

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

if len(sys.argv) != 2:
    print("Usage: python set_power.py <power_state>")
    print("Example: python set_power.py on")
    print("Example: python set_power.py off")
    sys.exit(1)

power_arg = sys.argv[1].lower()
if power_arg not in ['on', 'off', '1', '0']:
    print("Error: Power state must be 'on', 'off', '1', or '0'")
    sys.exit(1)

# Convert power argument to numeric value
if power_arg in ['on', '1']:
    power_value = 1
    power_text = "ON"
else:
    power_value = 0
    power_text = "OFF"

HP_IP = '192.168.5.204'
HP_PORT = 7000

AES_KEY = 'a3K8Bx%2r8Y7#xDh'
BLOCK_SIZE = 16

# Find message
FIND_MSG = {
    't': 'scan'
}

# Bind message
BIND_MSG = {
    'cid': 'app',
    'i': 1,
    't': 'pack',
    'uid': 0
}

BIND_PACK = {
    't': 'bind',
    'uid': 0
}

# Command message
CMD_MSG = {
    'cid': 'app',
    'i': 0,
    't': 'pack',
    'uid': 0
}

### Initialization
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', HP_PORT))
cipher = AES.new(AES_KEY.encode('utf-8'), AES.MODE_ECB)

### Decoding pack embedded in device's response
def parse_msg(msg, _cipher = cipher):
    decoded_pack64 = base64.b64decode(msg)
    decrypted_pack = unpad(_cipher.decrypt(decoded_pack64), BLOCK_SIZE)
    return json.loads(decrypted_pack)

### Encoding pack to send in device's message
def enc_msg(msg, _cipher = cipher):
    b_msg = json.dumps(msg).encode('utf-8')
    encoded_pack = _cipher.encrypt(pad(b_msg, BLOCK_SIZE))
    return base64.b64encode(encoded_pack).decode()

### Sending sock message
def send_msg(msg):
    b_msg = json.dumps(msg).encode('utf-8')
    sock.sendto(b_msg, (HP_IP, HP_PORT))

### Receiving sock message
def receive_msg(sock):
    data, addr = sock.recvfrom(1024)
    decoded_data = json.loads(data)
    return decoded_data

print(f"Setting heat pump power to {power_text}...")

# 1. Find message and reply
send_msg(FIND_MSG)
msg = receive_msg(sock)
pack = parse_msg(msg['pack'])
msg['pack'] = pack

print('#1 Discovery:', msg)

# 2. Binding to device
final_bind_pack = BIND_PACK.copy()
final_bind_pack['mac'] = pack['mac']

final_bind_msg = BIND_MSG.copy()
final_bind_msg['tcid'] = pack['mac']
final_bind_msg['pack'] = enc_msg(final_bind_pack)

send_msg(final_bind_msg)
msg = receive_msg(sock)
pack = parse_msg(msg['pack'])
msg['pack'] = pack

print('#2 Binding:', msg)

### Device specific encryption
DEVICE_KEY = pack['key']
device_cipher = AES.new(DEVICE_KEY.encode('utf-8'), AES.MODE_ECB)

# 3. Set power state
cmd_pack = {
    'mac': pack['mac'],
    't': 'cmd',
    'opt': ['Pow'],
    'p': [power_value]
}

final_cmd_msg = CMD_MSG.copy()
final_cmd_msg['tcid'] = pack['mac']
final_cmd_msg['pack'] = enc_msg(cmd_pack, device_cipher)

send_msg(final_cmd_msg)
msg = receive_msg(sock)
pack = parse_msg(msg['pack'], device_cipher)
msg['pack'] = pack

print('#3 Command result:', msg)
print(f"Heat pump power set to {power_text}")

sock.close()