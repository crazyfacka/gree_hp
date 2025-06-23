"""Number platform for Gree Heat Pump integration."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, UnitOfTemperature
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
    """Set up number platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    heat_pump = hass.data[DOMAIN][config_entry.entry_id]["heat_pump"]
    host = config_entry.data[CONF_HOST]

    entities = [
        GreeHeatPumpTemperature(coordinator,
                                heat_pump,
                                host,
                                "CoWatOutTemSet",
                                "Cold Water Temperature", 5, 30),
        GreeHeatPumpTemperature(coordinator,
                                heat_pump,
                                host,
                                "HeWatOutTemSet",
                                "Hot Water Temperature", 30, 60),
        GreeHeatPumpTemperature(coordinator,
                                heat_pump,
                                host,
                                "WatBoxTemSet",
                                "Shower Water Temperature", 30, 60),
    ]

    async_add_entities(entities)

class GreeHeatPumpTemperature(CoordinatorEntity, NumberEntity):
    """Number entity for Gree Heat Pump temperature control."""

    def __init__(self, coordinator, heat_pump, host, param_key, name, min_temp, max_temp):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._heat_pump = heat_pump
        self._host = host
        self._param_key = param_key
        self._attr_name = f"Gree Heat Pump {host} {name}"
        self._attr_unique_id = f"gree_hp_{host}_{param_key}"
        self._attr_native_min_value = min_temp
        self._attr_native_max_value = max_temp
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_mode = "slider"

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
    def native_value(self):
        """Return the current value."""
        data = self.coordinator.data
        if data and self._param_key in data:
            try:
                return float(data[self._param_key])
            except (ValueError, TypeError):
                return None
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set new temperature value."""
        temp_type_mapping = {
            "CoWatOutTemSet": "cold",
            "HeWatOutTemSet": "hot", 
            "WatBoxTemSet": "shower"
        }

        temp_type = temp_type_mapping.get(self._param_key)
        if temp_type:
            success = await self._heat_pump.async_set_temperature(temp_type, int(value))
            if success:
                # Request immediate update
                await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._heat_pump._is_rebinding and self._heat_pump._retry_count < self._heat_pump._max_retries:
            return True
        else:
            return self.coordinator.last_update_success
