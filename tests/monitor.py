import base64
import json
import socket
import time
from datetime import datetime

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

HP_IP = '192.168.5.204'
HP_PORT = 7000

AES_KEY = 'a3K8Bx%2r8Y7#xDh'
BLOCK_SIZE = 16

FIND_MSG = {
    't': 'scan'
}

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

STATUS_MSG = {
    'cid': 'app',
    'i': 0,
    't': 'pack',
    'uid': 0
}

MONITORED_FIELDS = [
    'AllInWatTemHi',
    'AllInWatTemLo', 
    'AllOutWatTemHi',
    'AllOutWatTemLo',
    'HepOutWatTemHi',
    'HepOutWatTemLo',
    'WatBoxTemHi',
    'WatBoxTemLo',
    'RmoHomTemHi',
    'RmoHomTemLo',
    'WatBoxElcHeRunSta'
]

# Temperature field pairs for Hi/Lo conversion
TEMPERATURE_PAIRS = [
    'AllInWatTem',
    'AllOutWatTem',
    'HepOutWatTem',
    'WatBoxTem',
    'RmoHomTem'
]

# All individual temperature fields
TEMPERATURE_FIELDS = [
    'AllInWatTemHi',
    'AllInWatTemLo', 
    'AllOutWatTemHi',
    'AllOutWatTemLo',
    'HepOutWatTemHi',
    'HepOutWatTemLo',
    'WatBoxTemHi',
    'WatBoxTemLo',
    'RmoHomTemHi',
    'RmoHomTemLo'
]

def parse_msg(msg, _cipher):
    decoded_pack64 = base64.b64decode(msg)
    decrypted_pack = unpad(_cipher.decrypt(decoded_pack64), BLOCK_SIZE)
    return json.loads(decrypted_pack)

def enc_msg(msg, _cipher):
    b_msg = json.dumps(msg).encode('utf-8')
    encoded_pack = _cipher.encrypt(pad(b_msg, BLOCK_SIZE))
    return base64.b64encode(encoded_pack).decode()

def send_msg(sock, msg):
    b_msg = json.dumps(msg).encode('utf-8')
    sock.sendto(b_msg, (HP_IP, HP_PORT))

def receive_msg(sock):
    data, addr = sock.recvfrom(1024)
    decoded_data = json.loads(data)
    return decoded_data

def initialize_connection():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10.0)
    sock.bind(('0.0.0.0', HP_PORT))
    cipher = AES.new(AES_KEY.encode('utf-8'), AES.MODE_ECB)
    
    # Find device
    send_msg(sock, FIND_MSG)
    msg = receive_msg(sock)
    pack = parse_msg(msg['pack'], cipher)
    
    # Bind to device
    final_bind_pack = BIND_PACK.copy()
    final_bind_pack['mac'] = pack['mac']
    
    final_bind_msg = BIND_MSG.copy()
    final_bind_msg['tcid'] = pack['mac']
    final_bind_msg['pack'] = enc_msg(final_bind_pack, cipher)
    
    send_msg(sock, final_bind_msg)
    msg = receive_msg(sock)
    pack = parse_msg(msg['pack'], cipher)
    
    # Get device-specific key
    device_key = pack['key']
    device_cipher = AES.new(device_key.encode('utf-8'), AES.MODE_ECB)
    mac_address = pack['mac']
    
    return sock, device_cipher, mac_address

def get_status(sock, device_cipher, mac_address):
    status_pack = {
        'mac': mac_address,
        't': 'status',
        'cols': MONITORED_FIELDS
    }
    
    final_status_msg = STATUS_MSG.copy()
    final_status_msg['tcid'] = mac_address
    final_status_msg['pack'] = enc_msg(status_pack, device_cipher)
    
    send_msg(sock, final_status_msg)
    msg = receive_msg(sock)
    pack = parse_msg(msg['pack'], device_cipher)
    
    # Handle different response structures
    dat = pack.get('dat', pack)
    if isinstance(dat, list):
        # If dat is a list, convert it to a dict using cols as keys
        dat_dict = {}
        for i, col in enumerate(MONITORED_FIELDS):
            if i < len(dat):
                dat_dict[col] = dat[i]
        dat = dat_dict
    
    return dat

def calculate_temperature(base_name, all_values):
    """Calculate temperature from Hi/Lo pair using formula (Hi-100)+Lo*0.1"""
    hi_field = base_name + 'Hi'
    lo_field = base_name + 'Lo'
    
    hi_value = all_values.get(hi_field, 'N/A')
    lo_value = all_values.get(lo_field, 'N/A')
    
    if hi_value == 'N/A' or lo_value == 'N/A':
        return 'N/A'
    
    try:
        temp_value = (float(hi_value) - 100.0) + (float(lo_value) * 0.1)
        return f"{temp_value:.1f}°C"
    except (ValueError, TypeError):
        return 'N/A'

def print_status_change(field, old_value, new_value, timestamp):
    print(f"[{timestamp}] {field}: {old_value} -> {new_value}")

def main():
    print("Gree Heat Pump Monitor")
    print("Monitoring fields:", ", ".join(MONITORED_FIELDS))
    print("Polling every 10 seconds...")
    print("=" * 60)
    
    try:
        sock, device_cipher, mac_address = initialize_connection()
        previous_values = {}
        
        while True:
            try:
                current_values = get_status(sock, device_cipher, mac_address)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Display current values and check for changes
                print(f"[{timestamp}] Current values:")
                
                # Process temperature pairs
                for temp_pair in TEMPERATURE_PAIRS:
                    current_temp = calculate_temperature(temp_pair, current_values)
                    previous_temp = calculate_temperature(temp_pair, previous_values)
                    
                    if previous_temp != 'N/A' and current_temp != previous_temp:
                        print(f"  {temp_pair}: {current_temp} (changed from {previous_temp})")
                    else:
                        print(f"  {temp_pair}: {current_temp}")
                
                # Process non-temperature fields
                for field in MONITORED_FIELDS:
                    if field not in TEMPERATURE_FIELDS:
                        current_value = current_values.get(field, 'N/A')
                        previous_value = previous_values.get(field, 'N/A')
                        
                        if previous_value != 'N/A' and current_value != previous_value:
                            print(f"  {field}: {current_value} (changed from {previous_value})")
                        else:
                            print(f"  {field}: {current_value}")
                        
                        previous_values[field] = current_value
                
                # Store all values for next comparison
                for field in MONITORED_FIELDS:
                    previous_values[field] = current_values.get(field, 'N/A')
                
                time.sleep(10)
                
            except socket.timeout:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Timeout - retrying connection...")
                sock.close()
                sock, device_cipher, mac_address = initialize_connection()
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
                time.sleep(10)
                
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        if 'sock' in locals():
            sock.close()

if __name__ == "__main__":
    main()