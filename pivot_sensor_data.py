#!/usr/bin/env python3
"""
Python script to pivot sensor data - one row per timestamp with entities as columns
Equivalent of PivotSensorData.ps1
"""

import pandas as pd
import numpy as np
import argparse
import sys
from pathlib import Path
from typing import Optional

def pivot_sensor_data(input_path: str, output_path: Optional[str] = None, 
                     time_interval_minutes: int = 1) -> bool:
    """
    Pivot sensor data from long format to wide format
    
    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file (optional)
        time_interval_minutes: Round timestamps to this interval in minutes (0 = no rounding)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if input file exists
        input_file = Path(input_path)
        if not input_file.exists():
            print(f"Error: Input file not found: {input_path}")
            return False
        
        # Set output path if not provided
        if output_path is None:
            stem = input_file.stem
            suffix = input_file.suffix
            directory = input_file.parent
            output_path = directory / f"{stem}_pivoted{suffix}"
        
        # Try to detect if file has headers by reading first line
        with open(input_path, 'r') as f:
            first_line = f.readline().strip()
        
        has_headers = any(keyword in first_line.lower() 
                         for keyword in ['entity_id', 'state', 'last_changed'])
        
        # Load the CSV data
        if has_headers:
            df = pd.read_csv(input_path)
            print(f"Loaded CSV with headers. Columns: {list(df.columns)}")
        else:
            df = pd.read_csv(input_path, names=['entity_id', 'state', 'last_changed'])
            print("Loaded CSV without headers, assigned standard column names")
        
        print(f"Processing {len(df)} records...")
        
        # Get unique entities to create columns
        entities = sorted(df['entity_id'].unique())
        print(f"Found entities: {', '.join(entities)}")
        
        # Convert timestamps
        df['timestamp'] = pd.to_datetime(df['last_changed'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        
        # Round timestamps to specified interval if needed
        if time_interval_minutes > 0:
            # Round down to the nearest interval
            df['rounded_timestamp'] = df['timestamp'].dt.floor(f'{time_interval_minutes}min')
        else:
            df['rounded_timestamp'] = df['timestamp']
        
        # Create timestamp string for output
        df['timestamp_str'] = df['rounded_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        # If multiple values exist for the same entity at the same rounded timestamp,
        # take the last one (most recent)
        df_sorted = df.sort_values(['entity_id', 'rounded_timestamp', 'timestamp'])
        df_latest = df_sorted.groupby(['entity_id', 'timestamp_str']).tail(1)
        
        # Create pivot table
        pivot_df = df_latest.pivot_table(
            index='timestamp_str',
            columns='entity_id', 
            values='state',
            aggfunc='last',  # In case there are still duplicates
            fill_value=0     # Fill missing values with 0
        )
        
        # Reset index to make timestamp_str a regular column
        pivot_df = pivot_df.reset_index()
        
        # Rename the timestamp column
        pivot_df = pivot_df.rename(columns={'timestamp_str': 'timestamp'})
        
        # Ensure all entities are present as columns (even if they have no data)
        for entity in entities:
            if entity not in pivot_df.columns:
                pivot_df[entity] = 0
        
        # Reorder columns: timestamp first, then entities in alphabetical order
        column_order = ['timestamp'] + sorted([col for col in pivot_df.columns if col != 'timestamp'])
        pivot_df = pivot_df[column_order]
        
        # Sort by timestamp
        pivot_df['temp_timestamp'] = pd.to_datetime(pivot_df['timestamp'])
        pivot_df = pivot_df.sort_values('temp_timestamp').drop('temp_timestamp')
        pivot_df = pivot_df.reset_index(drop=True)
        
        # Export to CSV
        pivot_df.to_csv(output_path, index=False)
        
        print("Successfully pivoted data")
        print(f"Input records: {len(df)}")
        print(f"Output records: {len(pivot_df)}")
        print(f"Entities as columns: {len(entities)}")
        print(f"Output file: {output_path}")
        
        if time_interval_minutes > 0:
            print(f"Time interval rounding: {time_interval_minutes} minute(s)")
        else:
            print("No time interval rounding applied")
        
        return True
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description='Pivot sensor data from long format to wide format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pivot_sensor_data.py sensor_data.csv
  python pivot_sensor_data.py data.csv --time-interval 5
  python pivot_sensor_data.py data.csv --time-interval 0  # No rounding
  python pivot_sensor_data.py input.csv --output pivoted_output.csv
        """
    )
    
    parser.add_argument('input_path', help='Path to input CSV file')
    parser.add_argument('--output', '-o', help='Path to output CSV file (optional)')
    parser.add_argument('--time-interval', '-t', type=int, default=1,
                       help='Round timestamps to this interval in minutes (default: 1, use 0 for no rounding)')
    
    args = parser.parse_args()
    
    # Process the data
    success = pivot_sensor_data(
        input_path=args.input_path,
        output_path=args.output,
        time_interval_minutes=args.time_interval
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()