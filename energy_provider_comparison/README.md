# Energy Provider Comparison Tool

A Python tool for comparing electricity providers using historical energy consumption and solar generation data. Supports complex time-of-use pricing structures with multiple pricing periods, weekday/weekend differences, and GST calculations.

## Features

- **Multi-tier Pricing Support**: Handle 2-tier, 3-tier, or custom pricing structures
- **Flexible Time Periods**: Define custom peak, off-peak, and night periods
- **Solar Feed-in Analysis**: Compare different buyback rates across providers
- **GST Support**: Optional 15% GST calculations per provider
- **Data Auto-detection**: Automatically identifies PV generation and consumption columns
- **Visual Analysis**: Generate comparison plots and detailed breakdowns
- **Excel Export**: Export detailed results for further analysis

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
# Compare providers using sample configuration
python energy_provider_comparison.py "your_data.csv" --plot

# Use custom provider configuration
python energy_provider_comparison.py "data.csv" --providers-config "custom_providers.json" --plot

# Export detailed results
python energy_provider_comparison.py "data.csv" --export "comparison_results.xlsx"
```

## Input Data Format

The tool accepts two input formats:

### 1. Home Assistant Export (Long Format)
```csv
entity_id,state,last_changed
sensor.solar_production,2.5,2024-01-01 12:00:00
sensor.home_consumption,1.8,2024-01-01 12:00:00
```

### 2. Pivoted Format (Recommended)
```csv
timestamp,sensor.solar_production,sensor.home_consumption
2024-01-01 12:00:00,2.5,1.8
2024-01-01 12:01:00,2.7,1.9
```

## Provider Configuration

### Simple 2-Tier Provider Example
```json
{
  "providers": [
    {
      "name": "Simple Provider",
      "daily_charge": 1.50,
      "time_periods": [
        {
          "name": "peak",
          "buy_price": 0.30,
          "buyback_price": 0.15,
          "time_ranges": [
            {"start_hour": 7, "end_hour": 21, "days": [0, 1, 2, 3, 4, 5, 6]}
          ]
        },
        {
          "name": "offpeak",
          "buy_price": 0.15,
          "buyback_price": 0.15,
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

### Complex 3-Tier Provider with GST
```json
{
  "providers": [
    {
      "name": "Complex Provider",
      "daily_charge": 2.50,
      "gst_applicable": true,
      "time_periods": [
        {
          "name": "peak",
          "buy_price": 0.35,
          "buyback_price": 0.20,
          "time_ranges": [
            {"start_hour": 7, "end_hour": 11, "days": [0, 1, 2, 3, 4]},
            {"start_hour": 17, "end_hour": 21, "days": [0, 1, 2, 3, 4]}
          ]
        },
        {
          "name": "offpeak",
          "buy_price": 0.25,
          "buyback_price": 0.15,
          "time_ranges": [
            {"start_hour": 11, "end_hour": 17, "days": [0, 1, 2, 3, 4]},
            {"start_hour": 21, "end_hour": 23, "days": [0, 1, 2, 3, 4]},
            {"start_hour": 7, "end_hour": 23, "days": [5, 6]}
          ]
        },
        {
          "name": "night",
          "buy_price": 0.15,
          "buyback_price": 0.10,
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

## Command Line Options

```
python energy_provider_comparison.py <data_file> [options]

Required:
  data_file                 Path to CSV file with energy data

Optional:
  --providers-config FILE   Custom provider configuration JSON file
  --pv-column NAME         Name of PV generation column
  --consumption-column NAME Name of consumption column
  --start-date DATE        Start date for analysis (YYYY-MM-DD)
  --end-date DATE          End date for analysis (YYYY-MM-DD)
  --plot                   Generate comparison plots
  --export FILE            Export results to Excel file
```

## Output Analysis

The tool provides:

1. **Cost Summary**: Total costs and daily averages per provider
2. **Savings Analysis**: Comparison between providers
3. **Visual Charts**: Cost breakdowns and monthly comparisons
4. **Detailed Excel Export**: Hourly data with cost calculations

## Testing

```bash
# Validate 3-tier pricing logic
python test_3tier_pricing.py
```

This validates the time-of-use pricing implementation across different scenarios.

## Configuration Notes

- **Days**: 0=Monday, 1=Tuesday, ..., 6=Sunday
- **Hours**: 0-23 (start_hour), 1-24 (end_hour, exclusive)
- **GST**: Applied to electricity purchases and daily charges only
- **Time Coverage**: All 24 hours must be covered by time periods

For more detailed configuration examples, see `sample_providers.json`.