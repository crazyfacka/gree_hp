import sys
import base64

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

AES_KEY = 'a3K8Bx%2r8Y7#xDh'
DEVICE_KEY = '8Bc1Ef4Hi7Kl0No3'
BLOCK_SIZE = 16

device = False
if len(sys.argv) > 1 and sys.argv[1] == 'd':
    device = True

msg = input('> ')

cipher = None
if device is True:
    cipher = AES.new(DEVICE_KEY.encode('utf-8'), AES.MODE_ECB)
else:
    cipher = AES.new(AES_KEY.encode('utf-8'), AES.MODE_ECB)

decoded_pack64 = base64.b64decode(msg)
decrypted_pack = unpad(cipher.decrypt(decoded_pack64), BLOCK_SIZE)

print(decrypted_pack)