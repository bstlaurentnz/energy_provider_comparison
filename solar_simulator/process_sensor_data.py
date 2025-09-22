#!/usr/bin/env python3
"""
Unified sensor data processing script
Combines functionality of both aggregate_data.py and pivot_sensor_data.py
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

def process_complete_pipeline(input_path: str, final_output_path: Optional[str] = None,
                             aggregation_method: str = "average", 
                             time_interval_minutes: int = 1,
                             keep_intermediate: bool = False) -> bool:
    """
    Process complete pipeline: aggregate -> pivot
    
    Args:
        input_path: Path to input CSV file
        final_output_path: Path to final output CSV file (optional)
        aggregation_method: Method to use for aggregation
        time_interval_minutes: Time interval for timestamp rounding in pivot step
        keep_intermediate: Whether to keep the intermediate aggregated file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        input_file = Path(input_path)
        
        # Step 1: Aggregate data
        print("="*60)
        print("STEP 1: AGGREGATING DATA")
        print("="*60)
        
        stem = input_file.stem
        suffix = input_file.suffix
        directory = input_file.parent
        
        # Intermediate file path
        intermediate_path = directory / f"{stem}_1min{suffix}"
        
        success = aggregate_sensor_data(
            input_path=input_path,
            output_path=str(intermediate_path),
            aggregation_method=aggregation_method
        )
        
        if not success:
            return False
        
        # Step 2: Pivot data
        print("\n" + "="*60)
        print("STEP 2: PIVOTING DATA")
        print("="*60)
        
        if final_output_path is None:
            final_output_path = directory / f"{stem}_processed{suffix}"
        
        success = pivot_sensor_data(
            input_path=str(intermediate_path),
            output_path=str(final_output_path),
            time_interval_minutes=time_interval_minutes
        )
        
        if not success:
            return False
        
        # Clean up intermediate file if not keeping it
        if not keep_intermediate:
            intermediate_path.unlink()
            print(f"Removed intermediate file: {intermediate_path}")
        
        print("\n" + "="*60)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Final output: {final_output_path}")
        
        return True
        
    except Exception as e:
        print(f"Error in pipeline: {e}")
        return False

def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description='Process sensor data: aggregate and/or pivot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline (aggregate + pivot)
  python process_sensor_data.py pipeline input.csv
  
  # Just aggregate data
  python process_sensor_data.py aggregate input.csv --method max
  
  # Just pivot data
  python process_sensor_data.py pivot aggregated.csv --time-interval 5
  
  # Complete pipeline with custom settings
  python process_sensor_data.py pipeline input.csv --output final.csv --method last --time-interval 0
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Aggregate command
    agg_parser = subparsers.add_parser('aggregate', help='Aggregate data into 1-minute intervals')
    agg_parser.add_argument('input_path', help='Path to input CSV file')
    agg_parser.add_argument('--output', '-o', help='Path to output CSV file (optional)')
    agg_parser.add_argument('--method', '-m', default='average',
                           choices=['average', 'mean', 'max', 'maximum', 'min', 'minimum', 'last'],
                           help='Aggregation method (default: average)')
    
    # Pivot command
    pivot_parser = subparsers.add_parser('pivot', help='Pivot data to wide format')
    pivot_parser.add_argument('input_path', help='Path to input CSV file')
    pivot_parser.add_argument('--output', '-o', help='Path to output CSV file (optional)')
    pivot_parser.add_argument('--time-interval', '-t', type=int, default=1,
                             help='Round timestamps to this interval in minutes (default: 1, use 0 for no rounding)')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete pipeline (aggregate + pivot)')
    pipeline_parser.add_argument('input_path', help='Path to input CSV file')
    pipeline_parser.add_argument('--output', '-o', help='Path to final output CSV file (optional)')
    pipeline_parser.add_argument('--method', '-m', default='average',
                                choices=['average', 'mean', 'max', 'maximum', 'min', 'minimum', 'last'],
                                help='Aggregation method (default: average)')
    pipeline_parser.add_argument('--time-interval', '-t', type=int, default=1,
                                help='Round timestamps to this interval in minutes (default: 1, use 0 for no rounding)')
    pipeline_parser.add_argument('--keep-intermediate', action='store_true',
                                help='Keep intermediate aggregated file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute the appropriate command
    success = False
    
    if args.command == 'aggregate':
        success = aggregate_sensor_data(
            input_path=args.input_path,
            output_path=args.output,
            aggregation_method=args.method
        )
    
    elif args.command == 'pivot':
        success = pivot_sensor_data(
            input_path=args.input_path,
            output_path=args.output,
            time_interval_minutes=args.time_interval
        )
    
    elif args.command == 'pipeline':
        success = process_complete_pipeline(
            input_path=args.input_path,
            final_output_path=args.output,
            aggregation_method=args.method,
            time_interval_minutes=args.time_interval,
            keep_intermediate=args.keep_intermediate
        )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()