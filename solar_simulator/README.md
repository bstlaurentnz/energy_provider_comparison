# Solar PV Battery Simulator

A comprehensive Python tool for simulating and analyzing the economic benefits of adding battery storage to solar PV systems. Uses Home Assistant sensor data to model optimal battery operation under time-of-use electricity pricing.

## Features

- **Complete Data Pipeline**: From raw Home Assistant exports to simulation results
- **Optimal Battery Control**: Smart charging/discharging based on time-of-use pricing
- **Economic Analysis**: Payback calculations, daily savings, and ROI analysis
- **Flexible Input Formats**: Supports both long-format and pivoted data
- **Auto-detection**: Automatically identifies PV and consumption data columns
- **Visualization**: Comprehensive plots showing battery operation and savings
- **Customizable Parameters**: Adjust battery specs, pricing, and system costs

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or using uv
uv pip install -r requirements.txt
```

### Basic Usage

```bash
# Complete pipeline: process raw data and run simulation
python process_sensor_data.py pipeline "raw_sensor_data.csv" --output "processed_data.csv"
python solar_simulation.py "processed_data.csv" --plot

# Or run individual steps:
# 1. Aggregate high-frequency data
python aggregate_data.py "raw_data.csv" --method average

# 2. Convert to simulation format
python pivot_sensor_data.py "raw_data_1min.csv"

# 3. Run simulation with visualization
python solar_simulation.py "raw_data_1min_pivoted.csv" --plot
```

## Input Data Formats

### Home Assistant Export (Long Format)
```csv
entity_id,state,last_changed
sensor.solar_production,2.5,2024-01-01 12:00:00
sensor.home_consumption,1.8,2024-01-01 12:00:00
sensor.solar_production,2.7,2024-01-01 12:01:00
sensor.home_consumption,1.9,2024-01-01 12:01:00
```

### Processed Format (Pivoted)
```csv
timestamp,sensor.solar_production,sensor.home_consumption
2024-01-01 12:00:00,2.5,1.8
2024-01-01 12:01:00,2.7,1.9
2024-01-01 12:02:00,2.4,2.1
```

## Data Processing Pipeline

### 1. Aggregation (`aggregate_data.py`)
Converts high-frequency sensor data into consistent time intervals:

```bash
# Default 1-minute averaging
python aggregate_data.py "raw_data.csv"

# Custom aggregation
python aggregate_data.py "raw_data.csv" --method sum --interval "5T"
```

**Options:**
- `--method`: average, sum, min, max, last
- `--interval`: pandas time interval (e.g., "1T", "5T", "15T")
- `--output`: custom output filename

### 2. Pivoting (`pivot_sensor_data.py`)
Converts long-format data to wide format suitable for simulation:

```bash
# Basic pivoting
python pivot_sensor_data.py "aggregated_data.csv"

# With custom parameters
python pivot_sensor_data.py "data.csv" --timestamp-column "custom_time" --output "pivoted_data.csv"
```

### 3. Unified Processing (`process_sensor_data.py`)
Combines aggregation and pivoting in a single command:

```bash
# Complete pipeline
python process_sensor_data.py pipeline "raw_data.csv" --output "ready_for_simulation.csv"

# Individual steps
python process_sensor_data.py aggregate "raw_data.csv"
python process_sensor_data.py pivot "raw_data_1min.csv"
```

## Battery Simulation

### Basic Simulation
```bash
# Default parameters (10kWh battery, 5kW charge/discharge rate)
python solar_simulation.py "data.csv"

# With visualization
python solar_simulation.py "data.csv" --plot
```

### Custom Battery Configuration
```bash
# Large residential system
python solar_simulation.py "data.csv" \
    --battery-capacity 20.0 \
    --charge-rate 10.0 \
    --discharge-rate 10.0 \
    --battery-efficiency 0.95 \
    --plot

# Custom pricing
python solar_simulation.py "data.csv" \
    --buy-price-peak 0.35 \
    --buy-price-offpeak 0.15 \
    --sell-price 0.12 \
    --peak-start 7 \
    --peak-end 21
```

### Economic Analysis
```bash
# Include battery cost for payback calculation
python solar_simulation.py "data.csv" \
    --battery-capacity 13.5 \
    --battery-cost 12000 \
    --plot
```

## Command Line Options

### `solar_simulation.py`
```
python solar_simulation.py <data_file> [options]

Required:
  data_file                CSV file with energy data

Battery Configuration:
  --battery-capacity FLOAT Battery capacity in kWh (default: 10.0)
  --charge-rate FLOAT      Max charge rate in kW (default: 5.0)
  --discharge-rate FLOAT   Max discharge rate in kW (default: 5.0)
  --battery-efficiency FLOAT Round-trip efficiency (default: 0.95)

Pricing:
  --buy-price-peak FLOAT   Peak electricity rate $/kWh (default: 0.26)
  --buy-price-offpeak FLOAT Off-peak rate $/kWh (default: 0.09)
  --sell-price FLOAT       Feed-in tariff $/kWh (default: 0.08)
  --peak-start INT         Peak period start hour (default: 7)
  --peak-end INT           Peak period end hour (default: 21)

Data:
  --pv-column NAME         PV generation column name
  --consumption-column NAME Consumption column name

Output:
  --plot                   Generate visualization plots
  --battery-cost FLOAT     Battery system cost for payback analysis
```

## Auto-Detection Features

The simulator automatically detects data columns using keywords:

- **PV Generation**: 'pv', 'solar', 'generation', 'gen'
- **Consumption**: 'consum', 'load', 'demand', 'use'

Override auto-detection with `--pv-column` and `--consumption-column` if needed.

## Simulation Algorithm

The battery operates with optimal control strategy:

1. **Morning/Day**: Charge with excess solar production
2. **Evening Peak**: Discharge to reduce grid consumption during expensive periods
3. **Night**: Remain idle unless arbitrage opportunities exist
4. **Export Control**: Balance between battery charging and grid export based on pricing

The algorithm respects:
- Battery capacity limits (0-100% SOC)
- Charge/discharge rate limits
- Round-trip efficiency losses
- Time-of-use pricing optimization

## Output Analysis

The simulation provides:

### Economic Metrics
- Annual costs with and without battery
- Daily average savings
- Payback period (if battery cost specified)
- Monthly breakdown of savings

### Operational Data
- Hourly battery state of charge
- Grid import/export patterns
- Energy flow analysis
- Battery utilization statistics

### Visualizations (with `--plot`)
- Battery SOC over time
- Daily energy flow patterns
- Monthly savings comparison
- Economic analysis charts

## Utility Scripts

### `convert_meter_data.py`
Converts utility meter data to simulation format:

```bash
python convert_meter_data.py "meter_data.csv" --output "converted_data.csv"
```

## Example Workflows

### Complete Analysis from Raw Data
```bash
# 1. Process raw Home Assistant export
python process_sensor_data.py pipeline "home_assistant_export.csv" --output "processed.csv"

# 2. Run simulation with custom battery
python solar_simulation.py "processed.csv" \
    --battery-capacity 13.5 \
    --battery-cost 15000 \
    --buy-price-peak 0.32 \
    --buy-price-offpeak 0.14 \
    --plot
```

### Quick Analysis with Pre-processed Data
```bash
# Direct simulation if data is already in correct format
python solar_simulation.py "pivoted_data.csv" --plot
```

### Testing Different Battery Sizes
```bash
# Small system
python solar_simulation.py "data.csv" --battery-capacity 5.0 --charge-rate 3.0

# Medium system
python solar_simulation.py "data.csv" --battery-capacity 10.0 --charge-rate 5.0

# Large system
python solar_simulation.py "data.csv" --battery-capacity 20.0 --charge-rate 10.0
```

## Data Quality Requirements

For accurate results, ensure:
- Consistent time intervals (preferably 1-minute or finer)
- Complete data coverage (minimal gaps)
- Proper unit alignment (kW for power, kWh for energy)
- Synchronized timestamps between PV and consumption data

The data processing pipeline helps address many of these requirements automatically.