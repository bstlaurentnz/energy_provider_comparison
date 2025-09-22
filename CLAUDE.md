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

### Data Processing Scripts
**PowerShell (Legacy):**
- `AggregateData.ps1`: Aggregates sensor data into consistent time intervals (default 1-minute)
- `PivotSensorData.ps1`: Converts long-format data to pivoted format suitable for simulation
- `csv2json.ps1`: Utility to convert CSV to JSON format

**Python (Recommended):**
- `aggregate_data.py`: Python equivalent of AggregateData.ps1 with improved error handling
- `pivot_sensor_data.py`: Python equivalent of PivotSensorData.ps1 with enhanced functionality
- `process_sensor_data.py`: Unified script that can run aggregate, pivot, or complete pipeline

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

**Python (Recommended):**
```bash
# Complete pipeline in one command
python process_sensor_data.py pipeline "history.csv" --output "processed_data.csv"

# Or run steps individually:
# 1. Aggregate raw sensor data to 1-minute intervals
python aggregate_data.py "history.csv" --method average

# 2. Pivot aggregated data to simulation format
python pivot_sensor_data.py "history_1min.csv"

# 3. Run simulation
python solar_simulation.py "history_1min_pivoted.csv" --plot
```

**PowerShell (Legacy):**
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

Energy providers require a structured JSON format with mandatory time period definitions. Each provider must define their complete pricing structure with custom time ranges.

### Required JSON Structure
```json
{
  "providers": [
    {
      "name": "Provider Name",
      "daily_charge": 1.50,           // $/day fixed daily charge (mandatory)
      "gst_applicable": false,        // Apply 15% GST to all costs (optional, default: false)
      "time_periods": [               // Array of pricing periods (mandatory)
        {
          "name": "peak",             // Period name (peak, offpeak, night, etc.)
          "buy_price": 0.35,          // $/kWh electricity purchase price
          "buyback_price": 0.10,      // $/kWh solar feed-in tariff
          "time_ranges": [            // Array of time ranges for this period
            {
              "start_hour": 7,        // Hour to start (0-23)
              "end_hour": 11,         // Hour to end (1-24, exclusive)
              "days": [0, 1, 2, 3, 4] // Days of week (0=Mon, 6=Sun)
            }
          ]
        }
      ]
    }
  ]
}
```

### Example: 3-Tier Pricing Provider
```json
{
  "providers": [
    {
      "name": "OctopusPeaker",
      "daily_charge": 2.872,
      "time_periods": [
        {
          "name": "peak",
          "buy_price": 0.312,
          "buyback_price": 0.40,
          "time_ranges": [
            {"start_hour": 7, "end_hour": 11, "days": [0, 1, 2, 3, 4]},
            {"start_hour": 17, "end_hour": 21, "days": [0, 1, 2, 3, 4]}
          ]
        },
        {
          "name": "offpeak",
          "buy_price": 0.243,
          "buyback_price": 0.10,
          "time_ranges": [
            {"start_hour": 11, "end_hour": 17, "days": [0, 1, 2, 3, 4]},
            {"start_hour": 21, "end_hour": 23, "days": [0, 1, 2, 3, 4]},
            {"start_hour": 7, "end_hour": 23, "days": [5, 6]}
          ]
        },
        {
          "name": "night",
          "buy_price": 0.156,
          "buyback_price": 0.05,
          "time_ranges": [
            {"start_hour": 23, "end_hour": 24, "days": [0, 1, 2, 3, 4, 5, 6]},
            {"start_hour": 0, "end_hour": 7, "days": [0, 1, 2, 3, 4, 5, 6]}
          ]
        }
      ]
    }
  ]
}
```

### Example: 2-Tier Pricing Provider
```json
{
  "providers": [
    {
      "name": "Meridian Solar",
      "daily_charge": 2.60,
      "time_periods": [
        {
          "name": "peak",
          "buy_price": 0.242,
          "buyback_price": 0.17,
          "time_ranges": [
            {"start_hour": 7, "end_hour": 21, "days": [0, 1, 2, 3, 4, 5, 6]}
          ]
        },
        {
          "name": "offpeak",
          "buy_price": 0.197,
          "buyback_price": 0.17,
          "time_ranges": [
            {"start_hour": 21, "end_hour": 24, "days": [0, 1, 2, 3, 4, 5, 6]},
            {"start_hour": 0, "end_hour": 7, "days": [0, 1, 2, 3, 4, 5, 6]}
          ]
        }
      ]
    }
  ]
}
```

### Example: Custom Business Hours Provider
```json
{
  "providers": [
    {
      "name": "Custom Business Hours Provider",
      "daily_charge": 1.50,
      "time_periods": [
        {
          "name": "peak",
          "buy_price": 0.35,
          "buyback_price": 0.10,
          "time_ranges": [
            {"start_hour": 9, "end_hour": 17, "days": [0, 1, 2, 3, 4]}
          ]
        },
        {
          "name": "offpeak",
          "buy_price": 0.15,
          "buyback_price": 0.10,
          "time_ranges": [
            {"start_hour": 17, "end_hour": 24, "days": [0, 1, 2, 3, 4]},
            {"start_hour": 0, "end_hour": 9, "days": [0, 1, 2, 3, 4]},
            {"start_hour": 0, "end_hour": 24, "days": [5, 6]}
          ]
        }
      ]
    }
  ]
}
```

**Key Features:**
- **Fully Customizable**: Define any number of pricing periods with custom names
- **Flexible Time Ranges**: Each period can have multiple time ranges
- **Day-of-Week Specific**: Different schedules for weekdays vs weekends
- **Multiple Time Blocks**: Peak hours can be split (e.g., morning and evening peaks)
- **Per-Provider Customization**: Each provider can have completely different time structures
- **GST Support**: Optional 15% GST can be applied to all costs per provider

### GST Configuration

The `gst_applicable` flag allows you to apply 15% GST (Goods and Services Tax) to costs for a provider:

- When `gst_applicable: true`: Energy purchase costs and daily charges are multiplied by 1.15
- When `gst_applicable: false` or omitted: No GST is applied (default behavior)
- GST is applied to energy purchases and daily charges only
- Solar buyback revenue is not affected by GST (revenue is not taxed)

Example with GST:
```json
{
  "name": "GST Provider",
  "daily_charge": 1.00,          // Will become $1.15/day with GST
  "gst_applicable": true,
  "time_periods": [
    {
      "name": "peak",
      "buy_price": 0.30,         // Purchases become $0.345/kWh with GST
      "buyback_price": 0.10,     // Remains $0.10/kWh (no GST on revenue)
      "time_ranges": [{"start_hour": 7, "end_hour": 21, "days": [0, 1, 2, 3, 4, 5, 6]}]
    }
  ]
}
```

See `sample_providers.json` for complete examples of all provider configuration formats.

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