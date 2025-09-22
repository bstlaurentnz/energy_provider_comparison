#!/usr/bin/env python3
"""
Convert meter usage data to format suitable for energy provider comparison
Input: CSV with daily rows for Feed-in and Consumption across 48 half-hourly columns
Output: CSV with timestamp, pv_generation_kw, consumption_kw columns
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse

def convert_meter_data(input_file, output_file=None):
    """
    Convert meter usage data from wide format (48 half-hourly columns)
    to long format (timestamp rows) suitable for energy provider comparison
    """

    print(f"Converting meter data: {input_file}")

    # Read the CSV file
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows")

    # Extract the time period columns (skip first 3 columns: ICP, Meter number, Meter element, Date)
    time_columns = df.columns[4:]  # 48 half-hourly columns
    print(f"Found {len(time_columns)} time period columns")

    results = []

    for idx, row in df.iterrows():
        date_str = row['Date']
        meter_element = row['Meter element']

        # Parse date - handle different formats
        try:
            if '/' in date_str:
                date = datetime.strptime(date_str, '%d/%m/%Y')
            else:
                date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print(f"Warning: Could not parse date '{date_str}', skipping row {idx}")
            continue

        # Process each 30-minute period
        for col_idx, time_col in enumerate(time_columns):
            # Extract start time from column name (e.g., "00:00 - 00:30" -> "00:00")
            start_time_str = time_col.split(' - ')[0]

            # Handle the midnight crossover (23:30 - 00:00)
            if start_time_str == "23:30":
                # This period goes from 23:30 to 00:00 (next day)
                timestamp = date.replace(hour=23, minute=30, second=0)
            else:
                hour, minute = map(int, start_time_str.split(':'))
                timestamp = date.replace(hour=hour, minute=minute, second=0)

            # Get energy value for this period
            energy_value = row[time_col]

            # Handle NaN or empty values
            if pd.isna(energy_value) or energy_value == '':
                energy_value = 0.0
            else:
                energy_value = float(energy_value)

            # Convert kWh to kW for 30-minute periods
            # For 30-minute intervals: kW = kWh * (60/30) = kWh * 2
            power_kw = energy_value * 2.0

            # Store result
            result = {
                'timestamp': timestamp,
                'meter_element': meter_element,
                'power_kw': power_kw
            }
            results.append(result)

    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    print(f"Created {len(results_df)} timestamp records")

    # Pivot to separate Feed-in and Consumption columns
    pivot_df = results_df.pivot_table(
        index='timestamp',
        columns='meter_element',
        values='power_kw',
        fill_value=0.0
    ).reset_index()

    # Rename columns to match expected format
    pivot_df.columns.name = None  # Remove the columns name

    # Create final output format with expected column names
    output_df = pd.DataFrame()
    output_df['timestamp'] = pivot_df['timestamp']

    # Map to expected column names
    if 'Feed-in' in pivot_df.columns:
        output_df['pv_generation_kw'] = pivot_df['Feed-in']
    else:
        output_df['pv_generation_kw'] = 0.0

    if 'Consumption' in pivot_df.columns:
        output_df['consumption_kw'] = pivot_df['Consumption']
    else:
        output_df['consumption_kw'] = 0.0

    # Sort by timestamp
    output_df = output_df.sort_values('timestamp').reset_index(drop=True)

    # Calculate summary statistics
    total_days = len(output_df['timestamp'].dt.date.unique())
    total_consumption_kwh = (output_df['consumption_kw'] * 0.5).sum()  # Convert back to kWh
    total_generation_kwh = (output_df['pv_generation_kw'] * 0.5).sum()  # Convert back to kWh

    print(f"\nData Summary:")
    print(f"Time range: {output_df['timestamp'].min()} to {output_df['timestamp'].max()}")
    print(f"Total days: {total_days}")
    print(f"Total records: {len(output_df)}")
    print(f"Total consumption: {total_consumption_kwh:.1f} kWh")
    print(f"Total generation: {total_generation_kwh:.1f} kWh")
    print(f"Net consumption: {total_consumption_kwh - total_generation_kwh:.1f} kWh")

    # Save output
    if output_file is None:
        output_file = input_file.replace('.csv', '_converted.csv')

    output_df.to_csv(output_file, index=False)
    print(f"\nConverted data saved to: {output_file}")

    return output_df

def main():
    parser = argparse.ArgumentParser(description='Convert meter usage data for energy provider comparison')
    parser.add_argument('input_file', help='Path to meter usage CSV file')
    parser.add_argument('-o', '--output', help='Output CSV file path')

    args = parser.parse_args()

    convert_meter_data(args.input_file, args.output)

if __name__ == '__main__':
    main()