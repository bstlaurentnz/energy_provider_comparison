# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a solar PV battery system simulation project that analyzes the economic impact of adding battery storage to a solar energy system. The project takes Home Assistant sensor data (typically from solar inverters and power meters) and simulates battery operation under time-of-use electricity pricing.

## Data Pipeline Architecture

The project uses a multi-stage data processing pipeline:

1. **Raw Data**: Home Assistant CSV exports with columns: `entity_id`, `state`, `last_changed`
2. **Aggregation**: PowerShell script aggregates high-frequency sensor data into 1-minute intervals
3. **Pivoting**: PowerShell script transforms long-format data into wide-format with timestamps as rows and entities as columns
4. **Simulation**: Python script runs the battery simulation on the processed data

## Key Components

### Data Processing Scripts (PowerShell)
- `AggregateData.ps1`: Aggregates sensor data into consistent time intervals (default 1-minute)
- `PivotSensorData.ps1`: Converts long-format data to pivoted format suitable for simulation
- `csv2json.ps1`: Utility to convert CSV to JSON format

### Core Simulation (`solar_simulation.py`)
- `SolarBatterySimulator` class: Main simulation engine
- Supports time-of-use pricing with configurable peak/off-peak hours and rates
- Handles both long-format and pre-pivoted data formats
- Auto-detects PV generation and consumption columns based on naming patterns

### Energy Provider Comparison (`energy_provider_comparison.py`)
- `EnergyProvider` dataclass: Represents provider pricing structure (peak/off-peak rates, solar buyback, daily charges)
- `EnergyProviderComparison` class: Compares multiple providers using historical data
- Supports JSON configuration files for provider definitions
- Calculates costs over any time period with detailed breakdowns and savings analysis

## Common Commands

### Data Processing Workflow
```powershell
# 1. Aggregate raw sensor data to 1-minute intervals
.\AggregateData.ps1 -InputPath "history.csv" -AggregationMethod "Average"

# 2. Pivot aggregated data to simulation format  
.\PivotSensorData.ps1 -InputPath "history_ag.csv"

# 3. Run simulation
python solar_simulation.py "history_ag_pivoted.csv" --plot
```

### Python Environment Setup
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

### Energy Provider Comparison
```bash
# Basic comparison using sample providers
python energy_provider_comparison.py "history_ag_pivoted.csv" --plot

# Using custom provider configuration file
python energy_provider_comparison.py "data.csv" --providers-config "sample_3tier_providers.json" --plot

# Analyze specific time period
python energy_provider_comparison.py "data.csv" --start-date "2024-01-01" --end-date "2024-01-31" --export "results.xlsx"

# Specify column names if auto-detection fails
python energy_provider_comparison.py "data.csv" --pv-column "sensor.solar_production" --consumption-column "sensor.home_consumption"
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

## Provider Configuration Format

Energy providers support both 2-tier and 3-tier time-of-use pricing:

### 3-Tier Pricing (Peak/Off-peak/Night)
```json
{
  "providers": [
    {
      "name": "3-Tier Provider",
      "peak_buy_price": 0.35,         // $/kWh peak hours (7-11am, 5-9pm weekdays)
      "offpeak_buy_price": 0.18,      // $/kWh off-peak (11am-5pm, 9-11pm weekdays, 7am-11pm weekends)
      "night_buy_price": 0.12,        // $/kWh night (11pm-7am every day)
      "peak_buyback_price": 0.10,     // $/kWh solar buyback during peak
      "offpeak_buyback_price": 0.08,  // $/kWh solar buyback during off-peak
      "night_buyback_price": 0.05,    // $/kWh solar buyback during night
      "daily_charge": 1.50             // $/day fixed daily charge
    }
  ]
}
```

### 2-Tier Pricing (Legacy format - still supported)
```json
{
  "providers": [
    {
      "name": "2-Tier Provider",
      "peak_buy_price": 0.28,         // $/kWh during peak hours (7am-9pm every day)
      "offpeak_buy_price": 0.12,      // $/kWh during off-peak hours (9pm-7am every day)
      "solar_buyback_price": 0.08,    // $/kWh single feed-in tariff
      "daily_charge": 1.20             // $/day fixed daily charge
    }
  ]
}
```

See `sample_providers.json` and `sample_3tier_providers.json` for examples.

## Testing and Validation

The project doesn't have formal unit tests. Validation is done through:
- Economic results review (payback period, daily savings)
- Visual inspection of plots showing battery operation
- Verification that battery SOC stays within bounds (0-100%)
- Checking that energy conservation is maintained (charge efficiency losses)
- Provider comparison validation by checking total costs against manual calculations

### Testing 3-Tier Pricing Logic
```bash
# Test the 3-tier time-of-use pricing implementation
python test_3tier_pricing.py
```
This validates that:
- Peak hours: 7-11am and 5-9pm on weekdays
- Off-peak hours: 11am-5pm and 9-11pm on weekdays, 7am-11pm on weekends  
- Night hours: 11pm-7am every day