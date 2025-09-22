# CLAUDE.md - Energy Provider Comparison

This directory contains the energy provider comparison tool that analyzes the economic impact of different electricity providers using historical energy data.

## Project Overview

The Energy Provider Comparison tool helps users evaluate different electricity providers by simulating their historical energy usage under various time-of-use pricing structures. It supports complex pricing schemes with multiple time periods, weekday/weekend differences, and GST calculations.

## Key Components

### Core Files
- `energy_provider_comparison.py`: Main comparison engine with `EnergyProvider` dataclass and `EnergyProviderComparison` class
- `test_3tier_pricing.py`: Validation script for testing 3-tier time-of-use pricing logic
- `sample_providers.json`: Example provider configurations demonstrating various pricing structures

### Dependencies
- `requirements.txt`: Python package dependencies
- `pyproject.toml`: Project configuration for uv package manager

## Common Commands

### Basic Usage
```bash
# Basic comparison using sample providers
python energy_provider_comparison.py "data.csv" --plot

# Using custom provider configuration file
python energy_provider_comparison.py "data.csv" --providers-config "sample_providers.json" --plot

# Analyze specific time period
python energy_provider_comparison.py "data.csv" --start-date "2024-01-01" --end-date "2024-01-31" --export "results.xlsx"

# Specify column names if auto-detection fails
python energy_provider_comparison.py "data.csv" --pv-column "sensor.solar_production" --consumption-column "sensor.home_consumption"
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or using uv (if available)
uv pip install -r requirements.txt
```

### Testing
```bash
# Test the 3-tier time-of-use pricing implementation
python test_3tier_pricing.py
```

## Input Data Requirements

### Data Formats
The tool accepts two input formats:

1. **Long Format** (Home Assistant export):
   - Columns: `entity_id`, `state`, `last_changed`
   - Will be automatically pivoted during loading

2. **Pivoted Format** (recommended):
   - Column: `timestamp` plus entity columns
   - One row per timestamp, entities as columns

### Column Auto-Detection
- **PV Generation**: Looks for keywords: 'pv', 'solar', 'generation', 'gen'
- **Consumption**: Looks for keywords: 'consum', 'load', 'demand', 'use'

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

### Example Configurations

**3-Tier Pricing Provider:**
```json
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
```

**2-Tier Pricing Provider:**
```json
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
```

See `sample_providers.json` for complete examples of all provider configuration formats.

## Key Features

- **Fully Customizable**: Define any number of pricing periods with custom names
- **Flexible Time Ranges**: Each period can have multiple time ranges
- **Day-of-Week Specific**: Different schedules for weekdays vs weekends
- **Multiple Time Blocks**: Peak hours can be split (e.g., morning and evening peaks)
- **Per-Provider Customization**: Each provider can have completely different time structures
- **GST Support**: Optional 15% GST can be applied to all costs per provider

## Validation and Testing

The tool provides validation through:
- Economic results review (total costs, daily averages)
- Visual plots showing cost breakdowns by provider
- Excel export for detailed analysis
- Time period validation ensuring complete coverage of all hours
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