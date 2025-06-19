# Gree Heat Pump Home Assistant Integration

This is a custom Home Assistant integration for Gree Heat Pump devices that use the proprietary UDP protocol.

## Installation

1. Copy the `gree_heat_pump` folder to your Home Assistant `custom_components` directory:
   ```
   custom_components/
     gree_heat_pump/
   ```

2. Restart Home Assistant

3. Go to Settings → Devices & Services → Add Integration

4. Search for "Gree Heat Pump" and click to add

5. Enter the IP address of your heat pump when prompted

## Features

The integration provides the following entities:

### Climate Entity
- **Power Control**: Turn the heat pump on/off
- **Mode Selection**: Cool, Heat, Hot Water, Cool + Hot Water, Heat + Hot Water
- **Temperature Control**: Set target temperatures

### Temperature Sensors
- **Cold Water Temperature**: Current cold water temperature setting
- **Hot Water Temperature**: Current hot water temperature setting  
- **Shower Water Temperature**: Current shower water temperature setting

### Power Switch
- **Power Switch**: Alternative way to control heat pump power state

## Configuration

During setup, you only need to provide:
- **IP Address**: The local IP address of your heat pump (e.g., 192.168.1.100)

All other protocol parameters (port, encryption keys) are hardcoded based on the Gree protocol specifications.

## Data Updates

The integration polls the heat pump every 3 seconds to retrieve the current status, ensuring the Home Assistant entities stay synchronized with any manual changes made on the heat pump itself.

## Technical Details

- **Protocol**: UDP communication on port 7000
- **Encryption**: AES-ECB with device-specific keys
- **Discovery**: Automatic device discovery and binding
- **Dependencies**: Requires `pycryptodome` package

## Troubleshooting

1. **Connection Issues**: Ensure the heat pump IP address is correct and the device is on the same network
2. **Entity Updates**: The integration updates every 3 seconds; manual changes may take a few seconds to reflect
3. **Logs**: Check Home Assistant logs for detailed error messages if the integration fails to connect

## Development

This integration is based on reverse-engineered Gree heat pump protocol communication patterns. The implementation follows Home Assistant integration best practices with proper async handling and coordinator-based updates.