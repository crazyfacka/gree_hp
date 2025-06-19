"""Select platform for Gree Heat Pump integration."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_MAPPING, MODE_REVERSE_MAPPING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    heat_pump = hass.data[DOMAIN][config_entry.entry_id]["heat_pump"]
    host = config_entry.data[CONF_HOST]

    async_add_entities([GreeHeatPumpModeSelect(coordinator, heat_pump, host)])


class GreeHeatPumpModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for Gree Heat Pump mode control."""

    def __init__(self, coordinator, heat_pump, host):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._heat_pump = heat_pump
        self._host = host
        self._attr_name = f"Gree Heat Pump {host} Mode"
        self._attr_unique_id = f"gree_hp_{host}_mode"
        self._attr_options = list(MODE_MAPPING.values())

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
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        data = self.coordinator.data
        if data and "Mod" in data:
            mode_number = data["Mod"]
            return MODE_MAPPING.get(mode_number, "auto")
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        mode_number = MODE_REVERSE_MAPPING.get(option)
        if mode_number is not None:
            success = await self._heat_pump.async_set_mode(mode_number)
            if success:
                # Request immediate update
                await self.coordinator.async_request_refresh()
