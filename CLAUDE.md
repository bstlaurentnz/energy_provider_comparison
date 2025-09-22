# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two main components for solar PV battery system analysis:

1. **Solar Simulator** (`solar_simulator/`): Simulates battery operation and economic benefits of adding battery storage to solar PV systems
2. **Energy Provider Comparison** (`energy_provider_comparison/`): Compares different electricity providers using historical energy data

Both tools use Home Assistant sensor data and support time-of-use electricity pricing for comprehensive economic analysis.

## Directory Structure

```
├── solar_simulator/           # Battery simulation and data processing tools
│   ├── solar_simulation.py    # Main battery simulation engine
│   ├── aggregate_data.py      # Data aggregation utility
│   ├── pivot_sensor_data.py   # Data format conversion
│   ├── process_sensor_data.py # Unified data processing pipeline
│   ├── convert_meter_data.py  # Meter data conversion utility
│   ├── CLAUDE.md             # Component-specific instructions
│   ├── README.md             # User documentation
│   ├── requirements.txt      # Dependencies
│   └── pyproject.toml        # Project configuration
│
├── energy_provider_comparison/ # Provider comparison analysis tools
│   ├── energy_provider_comparison.py # Main comparison engine
│   ├── test_3tier_pricing.py  # Testing utility
│   ├── sample_providers.json  # Example provider configurations
│   ├── CLAUDE.md             # Component-specific instructions
│   ├── README.md             # User documentation
│   ├── requirements.txt      # Dependencies
│   └── pyproject.toml        # Project configuration
│
└── CLAUDE.md                 # This file - main project overview
```

## Quick Start

### For Solar Battery Simulation
```bash
cd solar_simulator/
python process_sensor_data.py pipeline "your_data.csv" --output "processed_data.csv"
python solar_simulation.py "processed_data.csv" --plot
```

### For Energy Provider Comparison
```bash
cd energy_provider_comparison/
python energy_provider_comparison.py "your_data.csv" --plot
```

## Component-Specific Documentation

- **Solar Simulator**: See `solar_simulator/CLAUDE.md` and `solar_simulator/README.md` for detailed instructions on battery simulation, data processing, and economic analysis
- **Energy Provider Comparison**: See `energy_provider_comparison/CLAUDE.md` and `energy_provider_comparison/README.md` for provider configuration, pricing structures, and comparison analysis

Each component is self-contained with its own dependencies, documentation, and can be used independently.