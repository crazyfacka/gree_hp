"""Constants for the Gree Heat Pump integration."""

DOMAIN = "gree_hp"
DEFAULT_PORT = 7000
AES_KEY = "a3K8Bx%2r8Y7#xDh"
BLOCK_SIZE = 16

# Configuration constants
CONF_POLLING_INTERVAL = "polling_interval"
DEFAULT_POLLING_INTERVAL = 10

# Mode mapping
MODE_MAPPING = {
    1: "Heat",
    2: "Hot water",
    3: "Cool + Hot water",
    4: "Heat + Hot water",
    5: "Cool"
}

MODE_REVERSE_MAPPING = {v: k for k, v in MODE_MAPPING.items()}
