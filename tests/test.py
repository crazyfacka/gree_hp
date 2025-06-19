import base64
import json
import socket

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

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
    # Add 'pack'
    # Add 'tcid' with MAC address
}

BIND_PACK = {
    't': 'bind',
    'uid': 0
    # Add 'mac' with MAC address
}

# Status message
STATUS_MSG = {
    'cid': 'app',
    'i': 0,
    't': 'pack',
    'uid': 0
    # Add 'pack'
    # Add 'tcid' with MAC address
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

# 1. Find message and reply
send_msg(FIND_MSG)
msg = receive_msg(sock)
pack = parse_msg(msg['pack'])
msg['pack'] = pack

print('#1', msg)
print()

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

print('#2', msg)
print()

### Device specific encryption
DEVICE_KEY = pack['key']
device_cipher = AES.new(DEVICE_KEY.encode('utf-8'), AES.MODE_ECB)

# 3. Status
status_pack = {
    'mac': pack['mac'],
    't': 'status',
    'cols': [
        'Pow',
        'TemUn',
        "HeatCoolType"
    ]
}

final_status_msg = STATUS_MSG.copy()
final_status_msg['tcid'] = pack['mac']
final_status_msg['pack'] = enc_msg(status_pack, device_cipher)

send_msg(final_status_msg)
msg = receive_msg(sock)
pack = parse_msg(msg['pack'], device_cipher)
msg['pack'] = pack

print('#3', msg)