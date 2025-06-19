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
}

BIND_PACK = {
    't': 'bind',
    'uid': 0
}

# Status message
STATUS_MSG = {
    'cid': 'app',
    'i': 0,
    't': 'pack',
    'uid': 0
}

### Initialization
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(10.0)  # 10 second timeout
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

# 2. Binding to device
final_bind_pack = BIND_PACK.copy()
final_bind_pack['mac'] = pack['mac']

final_bind_msg = BIND_MSG.copy()
final_bind_msg['tcid'] = pack['mac']
final_bind_msg['pack'] = enc_msg(final_bind_pack)

send_msg(final_bind_msg)
msg = receive_msg(sock)
pack = parse_msg(msg['pack'])

### Device specific encryption
DEVICE_KEY = pack['key']
device_cipher = AES.new(DEVICE_KEY.encode('utf-8'), AES.MODE_ECB)

# 3. Get status
status_pack = {
    'mac': pack['mac'],
    't': 'status',
    'cols': [
        'Pow',
        'Mod',
        'CoWatOutTemSet',
        'HeWatOutTemSet',
        'WatBoxTemSet',
        'TemUn'
    ]
}

final_status_msg = STATUS_MSG.copy()
final_status_msg['tcid'] = pack['mac']
final_status_msg['pack'] = enc_msg(status_pack, device_cipher)

send_msg(final_status_msg)
msg = receive_msg(sock)
pack = parse_msg(msg['pack'], device_cipher)

# Pretty print status
print("=" * 40)
print("    GREE HEAT PUMP STATUS")
print("=" * 40)

# Handle different response structures
dat = pack.get('dat', pack)
if isinstance(dat, list):
    # If dat is a list, convert it to a dict using cols as keys
    cols = status_pack['cols']
    dat_dict = {}
    for i, col in enumerate(cols):
        if i < len(dat):
            dat_dict[col] = dat[i]
    dat = dat_dict

# Power status
power_status = "ON" if dat.get('Pow', 0) == 1 else "OFF"
print(f"Power:           {power_status}")

# Mode
mode_num = dat.get('Mod', 0)
mode_names = {
    0: "Auto",
    1: "Heat", # Valid
    2: "Hot water", # Valid
    3: "Cool + Hot water", # Valid
    4: "Heat + Hot water", # Valid
    5: "Cool" # Valid
}
mode_name = mode_names.get(mode_num, f"Unknown ({mode_num})")
print(f"Mode:            {mode_name}")

# Temperature unit
temp_unit = "°C" if dat.get('TemUn', 0) == 0 else "°F"

# Temperatures
cold_temp = dat.get('CoWatOutTemSet', 'N/A')
hot_temp = dat.get('HeWatOutTemSet', 'N/A')
shower_temp = dat.get('WatBoxTemSet', 'N/A')

print(f"Cold Water:      {cold_temp}{temp_unit if cold_temp != 'N/A' else ''}")
print(f"Hot Water:       {hot_temp}{temp_unit if hot_temp != 'N/A' else ''}")
print(f"Shower Water:    {shower_temp}{temp_unit if shower_temp != 'N/A' else ''}")

print("=" * 40)

sock.close()