"""Gree Heat Pump communication handler."""
import asyncio
import base64
import json
import logging
import socket
from typing import Dict, Any, Optional

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from .const import DEFAULT_PORT, AES_KEY, BLOCK_SIZE

_LOGGER = logging.getLogger(__name__)


class GreeHeatPump:
    """Handle communication with Gree Heat Pump."""

    def __init__(self, host: str):
        """Initialize the heat pump connection."""
        self._host = host
        self._data: Dict[str, Any] = {}

    async def async_update(self) -> Dict[str, Any]:
        """Update data from heat pump."""
        try:
            data = await self._get_status()
            self._data = data or {}
            return self._data
        except Exception as e:
            _LOGGER.error("Failed to update heat pump data: %s", e)
            return self._data

    async def _get_status(self) -> Optional[Dict[str, Any]]:
        """Get current status from heat pump."""
        try:
            loop = asyncio.get_event_loop()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            sock.bind(('0.0.0.0', DEFAULT_PORT))
            
            try:
                cipher = AES.new(AES_KEY.encode('utf-8'), AES.MODE_ECB)
                
                # Step 1: Discovery
                find_msg = {'t': 'scan'}
                await loop.run_in_executor(None, self._send_msg, sock, find_msg)
                response = await loop.run_in_executor(None, self._receive_msg, sock)
                pack = self._parse_msg(response['pack'], cipher)
                device_mac = pack['mac']

                # Step 2: Binding
                bind_pack = {'t': 'bind', 'uid': 0, 'mac': device_mac}
                bind_msg = {
                    'cid': 'app', 'i': 1, 't': 'pack', 'uid': 0,
                    'tcid': device_mac,
                    'pack': self._enc_msg(bind_pack, cipher)
                }
                await loop.run_in_executor(None, self._send_msg, sock, bind_msg)
                response = await loop.run_in_executor(None, self._receive_msg, sock)
                pack = self._parse_msg(response['pack'], cipher)
                device_key = pack['key']
                device_cipher = AES.new(device_key.encode('utf-8'), AES.MODE_ECB)

                # Step 3: Get status
                status_pack = {
                    'mac': device_mac, 't': 'status',
                    'cols': ['Pow', 'Mod', 'CoWatOutTemSet', 'HeWatOutTemSet', 'WatBoxTemSet']
                }
                status_msg = {
                    'cid': 'app', 'i': 0, 't': 'pack', 'uid': 0,
                    'tcid': device_mac,
                    'pack': self._enc_msg(status_pack, device_cipher)
                }
                await loop.run_in_executor(None, self._send_msg, sock, status_msg)
                response = await loop.run_in_executor(None, self._receive_msg, sock)
                pack = self._parse_msg(response['pack'], device_cipher)
                
                # Convert list response to dict
                if isinstance(pack.get('dat'), list):
                    cols = ['Pow', 'Mod', 'CoWatOutTemSet', 'HeWatOutTemSet', 'WatBoxTemSet']
                    dat_dict = {}
                    for i, col in enumerate(cols):
                        if i < len(pack['dat']):
                            dat_dict[col] = pack['dat'][i]
                    return dat_dict
                
                return pack.get('dat', {})
                
            finally:
                sock.close()
                
        except Exception as e:
            _LOGGER.error("Failed to get status: %s", e)
            return None

    async def async_set_power(self, power_on: bool) -> bool:
        """Set power state."""
        return await self._send_command('Pow', 1 if power_on else 0)

    async def async_set_temperature(self, temp_type: str, temperature: int) -> bool:
        """Set temperature for specified type."""
        temp_mapping = {
            'cold': 'CoWatOutTemSet',
            'hot': 'HeWatOutTemSet',
            'shower': 'WatBoxTemSet'
        }
        
        if temp_type not in temp_mapping:
            _LOGGER.error("Invalid temperature type: %s", temp_type)
            return False

        return await self._send_command(temp_mapping[temp_type], temperature)

    async def async_set_mode(self, mode: int) -> bool:
        """Set operating mode."""
        return await self._send_command('Mod', mode)

    async def _send_command(self, param: str, value: int) -> bool:
        """Send command to heat pump."""
        try:
            loop = asyncio.get_event_loop()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            sock.bind(('0.0.0.0', DEFAULT_PORT))
            
            try:
                cipher = AES.new(AES_KEY.encode('utf-8'), AES.MODE_ECB)
                
                # Step 1: Discovery
                find_msg = {'t': 'scan'}
                await loop.run_in_executor(None, self._send_msg, sock, find_msg)
                response = await loop.run_in_executor(None, self._receive_msg, sock)
                pack = self._parse_msg(response['pack'], cipher)
                device_mac = pack['mac']

                # Step 2: Binding
                bind_pack = {'t': 'bind', 'uid': 0, 'mac': device_mac}
                bind_msg = {
                    'cid': 'app', 'i': 1, 't': 'pack', 'uid': 0,
                    'tcid': device_mac,
                    'pack': self._enc_msg(bind_pack, cipher)
                }
                await loop.run_in_executor(None, self._send_msg, sock, bind_msg)
                response = await loop.run_in_executor(None, self._receive_msg, sock)
                pack = self._parse_msg(response['pack'], cipher)
                device_key = pack['key']
                device_cipher = AES.new(device_key.encode('utf-8'), AES.MODE_ECB)

                # Step 3: Send command
                cmd_pack = {
                    'mac': device_mac, 't': 'cmd',
                    'opt': [param], 'p': [value]
                }
                cmd_msg = {
                    'cid': 'app', 'i': 0, 't': 'pack', 'uid': 0,
                    'tcid': device_mac,
                    'pack': self._enc_msg(cmd_pack, device_cipher)
                }
                await loop.run_in_executor(None, self._send_msg, sock, cmd_msg)
                response = await loop.run_in_executor(None, self._receive_msg, sock)
                
                _LOGGER.debug("Command %s=%s sent successfully", param, value)
                return True
                
            finally:
                sock.close()
                
        except Exception as e:
            _LOGGER.error("Failed to send command %s=%s: %s", param, value, e)
            return False

    def _parse_msg(self, msg: str, cipher) -> Dict[str, Any]:
        """Parse encrypted message from device."""
        decoded_pack64 = base64.b64decode(msg)
        decrypted_pack = unpad(cipher.decrypt(decoded_pack64), BLOCK_SIZE)
        return json.loads(decrypted_pack)

    def _enc_msg(self, msg: Dict[str, Any], cipher) -> str:
        """Encrypt message to send to device."""
        b_msg = json.dumps(msg).encode('utf-8')
        encoded_pack = cipher.encrypt(pad(b_msg, BLOCK_SIZE))
        return base64.b64encode(encoded_pack).decode()

    def _send_msg(self, sock, msg: Dict[str, Any]) -> None:
        """Send message to device."""
        b_msg = json.dumps(msg).encode('utf-8')
        sock.sendto(b_msg, (self._host, DEFAULT_PORT))

    def _receive_msg(self, sock) -> Dict[str, Any]:
        """Receive message from device."""
        data, addr = sock.recvfrom(1024)
        return json.loads(data)

    @property
    def data(self) -> Dict[str, Any]:
        """Get current data."""
        return self._data