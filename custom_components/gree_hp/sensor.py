"""Support for Gree Heat Pump sensors."""
import logging
from typing import Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key="water_in_pe",
        name="Water In PE",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-water",
    ),
    SensorEntityDescription(
        key="water_out_pe",
        name="Water Out PE",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-water",
    ),
    SensorEntityDescription(
        key="water_tank",
        name="Water Tank",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-water",
    ),
]

# Mapping from sensor key to temperature field pairs
SENSOR_FIELD_MAPPING = {
    "water_in_pe": ("AllInWatTemHi", "AllInWatTemLo"),
    "water_out_pe": ("AllOutWatTemHi", "AllOutWatTemLo"),
    "water_tank": ("WatBoxTemHi", "WatBoxTemLo"),
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gree Heat Pump sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    host = config_entry.data[CONF_HOST]

    entities = []
    for description in SENSOR_DESCRIPTIONS:
        entities.append(GreeHeatPumpSensor(coordinator, description, host))

    async_add_entities(entities)

class GreeHeatPumpSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Gree Heat Pump sensor."""

    def __init__(self, coordinator, description: SensorEntityDescription, host: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._host = host
        self._attr_unique_id = f"gree_hp_{host}_{description.key}"
        self._attr_name = f"Gree Heat Pump {host} {description.name}"

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
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        sensor_key = self.entity_description.key
        if sensor_key not in SENSOR_FIELD_MAPPING:
            return None

        hi_field, lo_field = SENSOR_FIELD_MAPPING[sensor_key]
        hi_value = self.coordinator.data.get(hi_field)
        lo_value = self.coordinator.data.get(lo_field)

        if hi_value is None or lo_value is None:
            return None

        try:
            # Convert using formula (Hi-100)+Lo*0.1
            temperature = (float(hi_value) - 100.0) + (float(lo_value) * 0.1)
            return round(temperature, 1)
        except (ValueError, TypeError):
            _LOGGER.warning("Failed to convert temperature values: %s, %s", hi_value, lo_value)
            return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        heat_pump = self.hass.data[DOMAIN][self.coordinator.config_entry.entry_id]["heat_pump"]

        if heat_pump.is_rebinding and heat_pump.retry_count < heat_pump.max_retries:
            return self.native_value is not None

        return self.coordinator.last_update_success and self.native_value is not None
