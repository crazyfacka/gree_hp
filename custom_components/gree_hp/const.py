"""Constants for the Gree Heat Pump integration."""

DOMAIN = "gree_hp"
DEFAULT_PORT = 7000
AES_KEY = "a3K8Bx%2r8Y7#xDh"
BLOCK_SIZE = 16

# Mode mapping
MODE_MAPPING = {
    1: "heat", 
    2: "hot water",
    3: "cool + hot water",
    4: "heat + hot water",
    5: "cool"
}

MODE_REVERSE_MAPPING = {v: k for k, v in MODE_MAPPING.items()}
