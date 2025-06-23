"""Switch platform for Gree Heat Pump integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    heat_pump = hass.data[DOMAIN][config_entry.entry_id]["heat_pump"]
    host = config_entry.data[CONF_HOST]

    async_add_entities([GreeHeatPumpSwitch(coordinator, heat_pump, host)])

class GreeHeatPumpSwitch(CoordinatorEntity, SwitchEntity):
    """Switch for Gree Heat Pump power control."""

    def __init__(self, coordinator, heat_pump, host):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._heat_pump = heat_pump
        self._host = host
        self._attr_name = f"Gree Heat Pump {host}"
        self._attr_unique_id = f"gree_hp_{host}_power"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._host)},
            "name": f"Gree Heat Pump {self._host}",
            "manufacturer": "Gree",
            "model": "Heat Pump",
        }

    @property
    def is_on(self):
        """Return true if switch is on."""
        data = self.coordinator.data
        if data and "Pow" in data:
            return data["Pow"] == 1
        return None

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        success = await self._heat_pump.async_set_power(True)
        if success:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        success = await self._heat_pump.async_set_power(False)
        if success:
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._heat_pump.is_rebinding and self._heat_pump.retry_count < self._heat_pump.max_retries:
            return True
        else:
            return self.coordinator.last_update_success
