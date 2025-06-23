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
        self._sock: Optional[socket.socket] = None
        self._device_mac: Optional[str] = None
        self._device_key: Optional[str] = None
        self._device_cipher = None
        self._is_bound = False
        self._last_successful_data: Dict[str, Any] = {}
        self._retry_count = 0
        self._max_retries = 3
        self._is_rebinding = False

    def __del__(self):
        """Clean up socket on destruction."""
        self._close_connection()

    def _close_connection(self):
        """Close socket connection and reset state."""
        if self._sock:
            try:
                self._sock.close()
            except Exception: # pylint: disable=broad-except
                pass
            self._sock = None
        self._device_mac = None
        self._device_key = None
        self._device_cipher = None
        self._is_bound = False

    async def _ensure_connection(self) -> bool:
        """Ensure we have a valid connection and binding."""
        try:
            if not self._is_bound:
                await self._setup_connection()
            return self._is_bound
        except Exception as e: # pylint: disable=broad-except
            _LOGGER.error("Failed to ensure connection: %s", e)
            self._close_connection()
            return False

    async def _setup_connection(self) -> None:
        """Setup socket connection and perform discovery/binding."""
        loop = asyncio.get_event_loop()

        # Close any existing connection
        self._close_connection()

        # Create new socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(5.0)
        self._sock.bind(('0.0.0.0', DEFAULT_PORT))

        try:
            cipher = AES.new(AES_KEY.encode('utf-8'), AES.MODE_ECB)

            # Step 1: Discovery
            find_msg = {'t': 'scan'}
            await loop.run_in_executor(None, self._send_msg, self._sock, find_msg)
            response = await loop.run_in_executor(None, self._receive_msg, self._sock)
            pack = self._parse_msg(response['pack'], cipher)
            self._device_mac = pack['mac']

            # Step 2: Binding
            bind_pack = {'t': 'bind', 'uid': 0, 'mac': self._device_mac}
            bind_msg = {
                'cid': 'app', 'i': 1, 't': 'pack', 'uid': 0,
                'tcid': self._device_mac,
                'pack': self._enc_msg(bind_pack, cipher)
            }
            await loop.run_in_executor(None, self._send_msg, self._sock, bind_msg)
            response = await loop.run_in_executor(None, self._receive_msg, self._sock)
            pack = self._parse_msg(response['pack'], cipher)
            self._device_key = pack['key']
            self._device_cipher = AES.new(self._device_key.encode('utf-8'), AES.MODE_ECB)
            self._is_bound = True

            _LOGGER.debug("Successfully established connection and binding to device %s",
                          self._device_mac)

        except Exception as e:
            _LOGGER.error("Failed to setup connection: %s", e)
            self._close_connection()
            raise

    async def async_update(self) -> Dict[str, Any]:
        """Update data from heat pump with graceful rebinding."""
        try:
            data = await self._get_status()
            if data:
                self._data = data
                self._last_successful_data = data.copy()
                self._retry_count = 0
                self._is_rebinding = False
                return self._data
            else:
                if self._is_rebinding and self._retry_count < self._max_retries:
                    _LOGGER.warning("Rebinding in progress, using cached data")
                    return self._last_successful_data
                else:
                    self._data = {}
                    return self._data
        except Exception as e: # pylint: disable=broad-except
            _LOGGER.error("Failed to update heat pump data: %s", e)
            if self._is_rebinding and self._retry_count < self._max_retries:
                return self._last_successful_data
            return self._data

    async def _get_status(self) -> Optional[Dict[str, Any]]:
        """Get current status with graceful rebinding."""
        for attempt in range(self._max_retries):
            try:
                if not await self._ensure_connection():
                    self._is_rebinding = True
                    self._retry_count = attempt + 1
                    if attempt < self._max_retries - 1:
                        backoff_time = min(2 ** attempt, 10)
                        _LOGGER.debug("Waiting %d seconds before retry", backoff_time)
                        await asyncio.sleep(backoff_time)
                    continue

                loop = asyncio.get_event_loop()

                # Get status using cached connection
                status_pack = {
                    'mac': self._device_mac, 't': 'status',
                    'cols': ['Pow', 'Mod', 'CoWatOutTemSet', 'HeWatOutTemSet', 'WatBoxTemSet',
                            'AllInWatTemHi', 'AllInWatTemLo', 'AllOutWatTemHi', 'AllOutWatTemLo',
                            'WatBoxTemHi', 'WatBoxTemLo']
                }
                status_msg = {
                    'cid': 'app', 'i': 0, 't': 'pack', 'uid': 0,
                    'tcid': self._device_mac,
                    'pack': self._enc_msg(status_pack, self._device_cipher)
                }
                await loop.run_in_executor(None, self._send_msg, self._sock, status_msg)
                response = await loop.run_in_executor(None, self._receive_msg, self._sock)
                pack = self._parse_msg(response['pack'], self._device_cipher)

                # Convert list response to dict
                if isinstance(pack.get('dat'), list):
                    cols = ['Pow', 'Mod', 'CoWatOutTemSet', 'HeWatOutTemSet', 'WatBoxTemSet',
                           'AllInWatTemHi', 'AllInWatTemLo', 'AllOutWatTemHi', 'AllOutWatTemLo',
                           'WatBoxTemHi', 'WatBoxTemLo']
                    dat_dict = {}
                    for i, col in enumerate(cols):
                        if i < len(pack['dat']):
                            dat_dict[col] = pack['dat'][i]
                    self._is_rebinding = False
                    self._retry_count = 0
                    return dat_dict

                self._is_rebinding = False
                self._retry_count = 0
                return pack.get('dat', {})

            except Exception as e: # pylint: disable=broad-except
                _LOGGER.error("Failed to get status (attempt %d/%d): %s",
                              attempt + 1,
                              self._max_retries, e)
                self._is_rebinding = True
                self._retry_count = attempt + 1

                if attempt == self._max_retries - 1:
                    self._close_connection()
                    return None
                else:
                    self._partial_reset()
                    backoff_time = min(2 ** attempt, 10)
                    _LOGGER.debug("Waiting %d seconds before retry", backoff_time)
                    await asyncio.sleep(backoff_time)

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
        """Send command to heat pump with graceful rebinding."""
        for attempt in range(self._max_retries):
            try:
                if not await self._ensure_connection():
                    self._is_rebinding = True
                    self._retry_count = attempt + 1
                    if attempt < self._max_retries - 1:
                        backoff_time = min(2 ** attempt, 10)
                        _LOGGER.debug("Waiting %d seconds before retry", backoff_time)
                        await asyncio.sleep(backoff_time)
                    continue

                loop = asyncio.get_event_loop()

                # Send command using cached connection
                cmd_pack = {
                    'mac': self._device_mac, 't': 'cmd',
                    'opt': [param], 'p': [value]
                }
                cmd_msg = {
                    'cid': 'app', 'i': 0, 't': 'pack', 'uid': 0,
                    'tcid': self._device_mac,
                    'pack': self._enc_msg(cmd_pack, self._device_cipher)
                }
                await loop.run_in_executor(None, self._send_msg, self._sock, cmd_msg)
                response = await loop.run_in_executor(None, self._receive_msg, self._sock)

                _LOGGER.debug("Command %s=%s sent successfully", param, value)
                self._is_rebinding = False
                self._retry_count = 0
                return True

            except Exception as e: # pylint: disable=broad-except
                _LOGGER.error("Failed to send command %s=%s (attempt %d/%d): %s",
                              param,
                              value,
                              attempt + 1,
                              self._max_retries, e)
                self._is_rebinding = True
                self._retry_count = attempt + 1

                if attempt == self._max_retries - 1:
                    self._close_connection()
                    return False
                else:
                    self._partial_reset()
                    backoff_time = min(2 ** attempt, 10)
                    _LOGGER.debug("Waiting %d seconds before retry", backoff_time)
                    await asyncio.sleep(backoff_time)

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
        data = sock.recvfrom(1024)[0]
        return json.loads(data)

    def _partial_reset(self):
        """Reset connection state but preserve data for rebinding."""
        if self._sock:
            try:
                self._sock.close()
            except Exception: # pylint: disable=broad-except
                pass
            self._sock = None
        self._device_cipher = None
        self._is_bound = False

    @property
    def data(self) -> Dict[str, Any]:
        """Get current data."""
        return self._data
