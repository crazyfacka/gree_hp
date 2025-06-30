"""The Gree Heat Pump integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
from .gree_hp import GreeHeatPump

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.NUMBER, Platform.SELECT, Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gree Heat Pump from a config entry."""
    host = entry.data[CONF_HOST]
    
    # Get polling interval from options, defaulting to 10 seconds
    polling_interval = entry.options.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)

    # Create heat pump instance
    heat_pump = GreeHeatPump(host)

    # Create data update coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"gree_hp_{host}",
        update_method=heat_pump.async_update,
        update_interval=timedelta(seconds=polling_interval),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "heat_pump": heat_pump,
    }

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
