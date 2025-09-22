# CLAUDE.md - Solar Battery Simulator

This directory contains the solar PV battery system simulation tools that analyze the economic impact of adding battery storage to a solar energy system using Home Assistant sensor data.

## Project Overview

The Solar Battery Simulator analyzes battery storage systems under time-of-use electricity pricing. It processes Home Assistant sensor data (typically from solar inverters and power meters) and simulates optimal battery operation to maximize economic benefits.

## Data Pipeline Architecture

The project uses a multi-stage data processing pipeline:

1. **Raw Data**: Home Assistant CSV exports with columns: `entity_id`, `state`, `last_changed`
2. **Aggregation**: Aggregates high-frequency sensor data into consistent time intervals (default 1-minute)
3. **Pivoting**: Transforms long-format data into wide-format with timestamps as rows and entities as columns
4. **Simulation**: Runs battery simulation on the processed data

## Key Components

### Data Processing Scripts
- `aggregate_data.py`: Aggregates sensor data into consistent time intervals with improved error handling
- `pivot_sensor_data.py`: Converts long-format data to pivoted format suitable for simulation
- `process_sensor_data.py`: Unified script that can run aggregate, pivot, or complete pipeline
- `convert_meter_data.py`: Utility to convert meter data formats

### Core Simulation
- `solar_simulation.py`: Contains `SolarBatterySimulator` class - the main simulation engine
  - Supports time-of-use pricing with configurable peak/off-peak hours and rates
  - Handles both long-format and pre-pivoted data formats
  - Auto-detects PV generation and consumption columns based on naming patterns

### Dependencies
- `requirements.txt`: Python package dependencies
- `pyproject.toml`: Project configuration for uv package manager

## Common Commands

### Data Processing Workflow

**Complete Pipeline (Recommended):**
```bash
# Complete pipeline in one command
python process_sensor_data.py pipeline "history.csv" --output "processed_data.csv"
```

**Individual Steps:**
```bash
# 1. Aggregate raw sensor data to 1-minute intervals
python aggregate_data.py "history.csv" --method average

# 2. Pivot aggregated data to simulation format
python pivot_sensor_data.py "history_1min.csv"

# 3. Run simulation
python solar_simulation.py "history_1min_pivoted.csv" --plot
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or using uv (if available)
uv pip install -r requirements.txt
```

### Running Simulations
```bash
# Basic simulation with default parameters
python solar_simulation.py "data.csv"

# Simulation with custom battery specs and plotting
python solar_simulation.py "data.csv" --battery-capacity 13.5 --charge-rate 7.0 --plot

# Specify column names if auto-detection fails
python solar_simulation.py "data.csv" --pv-column "sensor.solar_production" --consumption-column "sensor.home_consumption"

# Custom time-of-use pricing
python solar_simulation.py "data.csv" --buy-price-peak 0.30 --buy-price-offpeak 0.12 --peak-start 7 --peak-end 21
```

## Data Format Requirements

### Input Data Formats
The simulator accepts two input formats:

1. **Long Format** (Home Assistant export):
   - Columns: `entity_id`, `state`, `last_changed`
   - Will be automatically pivoted during loading

2. **Pivoted Format** (recommended):
   - Column: `timestamp` plus entity columns
   - One row per timestamp, entities as columns

### Column Auto-Detection
- **PV Generation**: Looks for keywords: 'pv', 'solar', 'generation', 'gen'
- **Consumption**: Looks for keywords: 'consum', 'load', 'demand', 'use'

## Key Configuration Parameters

### Battery System
- `battery_capacity`: Battery capacity in kWh (default: 10.0)
- `battery_efficiency`: Round-trip efficiency (default: 0.95)
- `max_charge_rate` / `max_discharge_rate`: Power limits in kW (default: 5.0)

### Economic Settings
- `grid_buy_price_peak` / `grid_buy_price_offpeak`: Time-of-use electricity rates (default: $0.26 / $0.09)
- `peak_start_hour` / `peak_end_hour`: Peak pricing period (default: 7-21)
- `grid_sell_price`: Feed-in tariff rate (default: $0.08)
- `battery_cost`: System cost for payback analysis (default: $8000)

## Data Processing Details

### Aggregation (`aggregate_data.py`)
- Aggregates high-frequency sensor data into consistent time intervals
- Supports multiple aggregation methods: average, sum, min, max, last
- Handles missing data and irregular timestamps
- Outputs files with `_1min` suffix for 1-minute aggregation

### Pivoting (`pivot_sensor_data.py`)
- Converts long-format Home Assistant data to wide format
- Creates timestamp column as index with entity_ids as columns
- Handles numeric conversion and missing values
- Outputs files with `_pivoted` suffix

### Unified Processing (`process_sensor_data.py`)
- Combines aggregation and pivoting in single command
- Supports pipeline mode for complete workflow
- Provides individual step execution for debugging
- Handles file naming and intermediate outputs

### Meter Data Conversion (`convert_meter_data.py`)
- Converts utility meter data formats to simulator-compatible format
- Handles different timestamp formats and data structures
- Useful for incorporating utility data alongside Home Assistant data

## Simulation Algorithm

The `SolarBatterySimulator` implements an optimal battery control strategy:

1. **Priority 1**: Charge battery with excess solar during cheap electricity periods
2. **Priority 2**: Use battery to avoid grid purchases during expensive periods
3. **Priority 3**: Export excess solar when beneficial
4. **Constraints**: Respect battery capacity, charge/discharge rates, and efficiency losses

The simulation calculates:
- Hourly battery state of charge (SOC)
- Grid import/export quantities
- Economic costs with and without battery
- Payback period and daily savings

## Testing and Validation

The project validates results through:
- Economic results review (payback period, daily savings)
- Visual inspection of plots showing battery operation
- Verification that battery SOC stays within bounds (0-100%)
- Checking that energy conservation is maintained (charge efficiency losses)
- Battery operation logic verification (optimal charge/discharge timing)

## Visualization Features

When using the `--plot` flag, the simulator generates:
- Battery state of charge over time
- Grid import/export patterns
- Economic comparison charts
- Daily/monthly savings analysis
- Energy flow diagrams

## Advanced Usage

### Custom Data Processing
```bash
# Aggregate with specific method and interval
python aggregate_data.py "data.csv" --method sum --interval "5T"

# Pivot with custom timestamp handling
python pivot_sensor_data.py "data.csv" --timestamp-column "custom_time"
```

### Simulation with Custom Parameters
```bash
# Large battery system with high charge rates
python solar_simulation.py "data.csv" --battery-capacity 20.0 --charge-rate 10.0 --discharge-rate 10.0

# Different pricing structure
python solar_simulation.py "data.csv" --buy-price-peak 0.35 --buy-price-offpeak 0.15 --sell-price 0.12

# Custom peak hours
python solar_simulation.py "data.csv" --peak-start 8 --peak-end 20
```

The simulator automatically handles data format detection, column identification, and economic optimization to provide comprehensive analysis of battery storage benefits.