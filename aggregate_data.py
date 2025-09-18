#!/usr/bin/env python3
"""
Python script to aggregate sensor data into 1-minute intervals
Equivalent of AggregateData.ps1
"""

import pandas as pd
import numpy as np
import argparse
import sys
from pathlib import Path
from typing import Optional

def aggregate_sensor_data(input_path: str, output_path: Optional[str] = None, 
                         aggregation_method: str = "average") -> bool:
    """
    Aggregate sensor data into 1-minute intervals
    
    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file (optional)
        aggregation_method: Method to use for aggregation (average, max, min, last)
        
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
            output_path = directory / f"{stem}_1min{suffix}"
        
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
        
        # Filter out "unknown" values and invalid states
        initial_count = len(df)
        df = df[df['state'].notna() & (df['state'] != '') & (df['state'] != 'unknown')]
        
        # Convert state to numeric, dropping non-numeric values
        df['state'] = pd.to_numeric(df['state'], errors='coerce')
        df = df.dropna(subset=['state'])
        
        # Convert timestamps
        df['timestamp'] = pd.to_datetime(df['last_changed'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        
        filtered_count = len(df)
        if initial_count > filtered_count:
            print(f"Filtered out {initial_count - filtered_count} invalid records")
        
        # Create minute intervals (round down to nearest minute)
        df['minute'] = df['timestamp'].dt.floor('1min')
        df['minute_str'] = df['minute'].dt.strftime('%Y-%m-%d %H:%M:00.000Z')
        
        # Group by entity_id and minute interval
        aggregation_methods = {
            'average': 'mean',
            'mean': 'mean',
            'max': 'max',
            'maximum': 'max', 
            'min': 'min',
            'minimum': 'min',
            'last': 'last'
        }
        
        agg_method = aggregation_methods.get(aggregation_method.lower(), 'mean')
        
        if agg_method == 'last':
            # For 'last', we need to sort by timestamp within each group
            df_sorted = df.sort_values(['entity_id', 'minute', 'timestamp'])
            aggregated = df_sorted.groupby(['entity_id', 'minute_str']).tail(1)[['entity_id', 'state', 'minute_str']]
        else:
            # For statistical aggregation methods
            aggregated = df.groupby(['entity_id', 'minute_str'])['state'].agg(agg_method).reset_index()
        
        # Round the aggregated values to 3 decimal places
        aggregated['state'] = aggregated['state'].round(3)
        
        # Rename columns to match PowerShell output format
        aggregated = aggregated.rename(columns={
            'minute_str': 'last_changed'
        })
        
        # Sort by entity_id and timestamp
        aggregated = aggregated.sort_values(['entity_id', 'last_changed']).reset_index(drop=True)
        
        # Export to CSV
        aggregated.to_csv(output_path, index=False)
        
        print("Successfully aggregated data into 1-minute intervals")
        print(f"Input records: {initial_count}")
        print(f"Output records: {len(aggregated)}")
        print(f"Output file: {output_path}")
        print(f"Aggregation method: {aggregation_method}")
        
        return True
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description='Aggregate sensor data into 1-minute intervals',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python aggregate_data.py input.csv
  python aggregate_data.py input.csv --output output_1min.csv
  python aggregate_data.py input.csv --method max
  python aggregate_data.py input.csv --method last --output aggregated.csv
        """
    )
    
    parser.add_argument('input_path', help='Path to input CSV file')
    parser.add_argument('--output', '-o', help='Path to output CSV file (optional)')
    parser.add_argument('--method', '-m', default='average',
                       choices=['average', 'mean', 'max', 'maximum', 'min', 'minimum', 'last'],
                       help='Aggregation method (default: average)')
    
    args = parser.parse_args()
    
    # Process the data
    success = aggregate_sensor_data(
        input_path=args.input_path,
        output_path=args.output,
        aggregation_method=args.method
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()