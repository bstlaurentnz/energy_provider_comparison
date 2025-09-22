#!/usr/bin/env python3
"""
Energy Provider Comparison Simulation
Compares different electricity providers using historical solar and consumption data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional
from dataclasses import field
import json

@dataclass
class TimeOfUsePeriod:
    """Represents a time-of-use pricing period"""
    name: str
    buy_price: float
    buyback_price: float
    time_ranges: List[Dict]  # List of {"start_hour": int, "end_hour": int, "days": List[int]}

@dataclass
class EnergyProvider:
    """Represents an energy provider with their pricing structure"""
    name: str
    daily_charge: float             # $/day fixed daily charge
    time_periods: List[TimeOfUsePeriod]  # Time-of-use periods (now mandatory)
    gst_applicable: bool = False    # Apply 15% GST to all costs if True
    
    def get_pricing(self, timestamp: pd.Timestamp) -> tuple:
        """Get the electricity buy and buyback price for a given timestamp"""
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Check each time period to find the matching one
        if self.time_periods:
            for period in self.time_periods:
                for time_range in period.time_ranges:
                    if (day_of_week in time_range["days"] and
                        self._hour_in_range(hour, time_range["start_hour"], time_range["end_hour"])):
                        return period.buy_price, period.buyback_price, period.name
        
        # Fallback to first period if no match found
        if self.time_periods:
            return self.time_periods[0].buy_price, self.time_periods[0].buyback_price, "unknown"
        
        return 0.0, 0.0, "unknown"
    
    def _hour_in_range(self, hour: int, start_hour: int, end_hour: int) -> bool:
        """Check if hour is within the specified range, handling midnight crossover"""
        if end_hour > start_hour:
            return start_hour <= hour < end_hour
        else:
            # Handle midnight crossover (e.g., 23-7)
            return hour >= start_hour or hour < end_hour
    
    def get_buy_price(self, timestamp: pd.Timestamp) -> float:
        """Legacy method for backward compatibility"""
        buy_price, _, _ = self.get_pricing(timestamp)
        return buy_price
    
    def get_buyback_price(self, timestamp: pd.Timestamp) -> float:
        """Get the solar buyback price for a given timestamp"""
        _, buyback_price, _ = self.get_pricing(timestamp)
        return buyback_price
    
    def get_daily_charge(self, date: pd.Timestamp) -> float:
        """Get the daily charge for a given date"""
        charge = self.daily_charge
        if self.gst_applicable:
            charge *= 1.15  # Apply 15% GST
        return charge

class EnergyProviderComparison:
    """Simulates energy costs across multiple providers using historical data"""
    
    def __init__(self):
        self.providers: Dict[str, EnergyProvider] = {}
        self.data: Optional[pd.DataFrame] = None
        self.pv_column: Optional[str] = None
        self.consumption_column: Optional[str] = None
        self.results: Dict[str, pd.DataFrame] = {}
        self.interval_minutes: Optional[float] = None
        self.data_start_date: Optional[pd.Timestamp] = None
        self.data_end_date: Optional[pd.Timestamp] = None
        self.total_days: Optional[int] = None
        
    def add_provider(self, provider: EnergyProvider):
        """Add an energy provider to the comparison"""
        self.providers[provider.name] = provider
        print(f"Added provider: {provider.name}")
    
    def add_providers_from_config(self, config_path: str):
        """Load providers from a JSON configuration file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            for provider_data in config['providers']:
                # Convert time_periods from dict format to TimeOfUsePeriod objects
                time_periods = []
                for period_data in provider_data['time_periods']:
                    time_period = TimeOfUsePeriod(
                        name=period_data['name'],
                        buy_price=period_data['buy_price'],
                        buyback_price=period_data['buyback_price'],
                        time_ranges=period_data['time_ranges']
                    )
                    time_periods.append(time_period)

                provider = EnergyProvider(
                    name=provider_data['name'],
                    daily_charge=provider_data['daily_charge'],
                    time_periods=time_periods,
                    gst_applicable=provider_data.get('gst_applicable', False)
                )
                self.add_provider(provider)

        except Exception as e:
            print(f"Error loading provider config: {e}")
            return False
        return True
    
    def load_data(self, csv_path: str):
        """Load and prepare historical data from CSV file"""
        try:
            df = pd.read_csv(csv_path)
            
            # Handle different data formats (same as original solar_simulation.py)
            if 'timestamp' in df.columns:
                self.data = df.copy()
                print(f"Loaded pivoted data with {len(df)} rows and columns: {list(df.columns)}")
            else:
                # Assume long format and pivot
                df_pivot = df.pivot_table(
                    index='last_changed' if 'last_changed' in df.columns else 'timestamp',
                    columns='entity_id',
                    values='state',
                    aggfunc='mean'
                ).reset_index()
                
                df_pivot.rename(columns={str(df_pivot.columns[0]): 'timestamp'}, inplace=True)
                self.data = df_pivot
                print(f"Pivoted long format data to {len(df_pivot)} rows and columns: {list(df_pivot.columns)}")
            
            # Ensure timestamp is datetime
            if 'timestamp' in self.data.columns:
                self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
                self.data = self.data.sort_values('timestamp').reset_index(drop=True)

                # Calculate data time span
                self.data_start_date = self.data['timestamp'].min()
                self.data_end_date = self.data['timestamp'].max()
                self.total_days = (self.data_end_date - self.data_start_date).days + 1

                print(f"Data time span: {self.data_start_date.strftime('%Y-%m-%d')} to {self.data_end_date.strftime('%Y-%m-%d')} ({self.total_days} days)")

            # Fill NaN values with 0
            self.data = self.data.fillna(0)
            
            return True
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def identify_columns(self, pv_column: Optional[str] = None, consumption_column: Optional[str] = None):
        """Identify or set the PV generation and consumption columns"""
        if self.data is None:
            raise ValueError("Data not loaded. Run load_data() first.")
        
        columns = [col for col in self.data.columns if col != 'timestamp']
        
        print(f"Available columns: {columns}")
        
        if pv_column is None:
            # Auto-detect PV column
            pv_candidates = [col for col in columns if any(keyword in col.lower() 
                           for keyword in ['pv', 'solar', 'generation', 'gen'])]
            if pv_candidates:
                pv_column = pv_candidates[0]
                print(f"Auto-detected PV column: {pv_column}")
            else:
                print("Could not auto-detect PV column. Please specify manually.")
                return False
        
        if consumption_column is None:
            # Auto-detect consumption column
            consumption_candidates = [col for col in columns if any(keyword in col.lower() 
                                    for keyword in ['consum', 'load', 'demand', 'use'])]
            if consumption_candidates:
                consumption_column = consumption_candidates[0]
                print(f"Auto-detected consumption column: {consumption_column}")
            else:
                print("Could not auto-detect consumption column. Please specify manually.")
                return False
        
        self.pv_column = pv_column
        self.consumption_column = consumption_column
        
        # Verify columns exist
        if pv_column not in self.data.columns:
            print(f"PV column '{pv_column}' not found in data")
            return False
        if consumption_column not in self.data.columns:
            print(f"Consumption column '{consumption_column}' not found in data")
            return False
            
        return True
    
    def simulate_provider(self, provider_name: str) -> pd.DataFrame:
        """Simulate costs for a single provider"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        if not hasattr(self, 'pv_column') or not hasattr(self, 'consumption_column'):
            raise ValueError("PV and consumption columns not identified. Run identify_columns() first.")
        
        if self.data is None:
            raise ValueError("Data not loaded. Run load_data() first.")
        
        provider = self.providers[provider_name]
        results = []

        # Detect and store the time interval from the data
        if self.interval_minutes is None:
            if len(self.data) >= 2:
                time_diff = self.data['timestamp'].iloc[1] - self.data['timestamp'].iloc[0]
                self.interval_minutes = time_diff.total_seconds() / 60.0
            else:
                self.interval_minutes = 1.0  # Default to 1-minute if only one row

        interval_minutes = self.interval_minutes
        print(f"Detected time interval: {interval_minutes} minutes")

        for idx, row in self.data.iterrows():
            pv_power = row[self.pv_column]
            consumed_power = row[self.consumption_column]

            # Convert power (kW) to energy (kWh) based on detected interval
            # kWh = kW * (interval_minutes / 60)
            pv_energy = pv_power * (interval_minutes / 60.0)  # kWh for this timestep
            consumed_energy = consumed_power * (interval_minutes / 60.0)  # kWh for this timestep
            net_energy = pv_energy - consumed_energy  # Positive = excess, Negative = deficit
            
            timestamp = pd.Timestamp(row['timestamp'])
            buy_price, buyback_price, period_name = provider.get_pricing(timestamp)
            
            # Calculate grid transactions in kWh
            grid_purchase = max(0.0, float(-net_energy))  # Buy when consumption exceeds generation
            grid_sale = max(0.0, float(net_energy))       # Sell excess generation
            
            # Calculate costs for this timestep
            purchase_cost = grid_purchase * buy_price
            sale_revenue = grid_sale * buyback_price

            # Apply GST only to purchases, not to sales revenue
            if provider.gst_applicable:
                purchase_cost *= 1.15  # Apply 15% GST to energy purchases only

            energy_cost = purchase_cost - sale_revenue
            
            result = {
                'timestamp': timestamp,
                'interval_minutes': interval_minutes,
                'pv_power': pv_power,
                'consumed_power': consumed_power,
                'pv_energy': pv_energy,
                'consumed_energy': consumed_energy,
                'net_energy': net_energy,
                'grid_purchase': grid_purchase,
                'grid_sale': grid_sale,
                'buy_price': buy_price,
                'buyback_price': buyback_price,
                'period_name': period_name,
                'energy_cost': energy_cost
            }
            results.append(result)
        
        results_df = pd.DataFrame(results)
        results_df['date'] = results_df['timestamp'].dt.date
        
        # Calculate daily aggregations
        daily_summary = results_df.groupby('date').agg({
            'energy_cost': 'sum',
            'timestamp': 'first'  # Get first timestamp for each day to calculate daily charge
        }).reset_index()

        # Add daily charges (once per day)
        daily_summary['daily_charge'] = daily_summary['timestamp'].apply(provider.get_daily_charge)
        daily_summary['total_daily_cost'] = daily_summary['energy_cost'] + daily_summary['daily_charge']

        # Merge daily totals back to timestep data for detailed analysis
        results_df = results_df.merge(
            daily_summary[['date', 'daily_charge', 'total_daily_cost']],
            on='date',
            how='left'
        )

        # For timestep-level analysis, we'll keep energy_cost per timestep
        # and show daily_charge and total_daily_cost at the daily level
        results_df['total_cost'] = results_df['energy_cost']  # Timestep-level energy cost only
        
        return results_df
    
    def run_comparison(self) -> Dict[str, pd.DataFrame]:
        """Run simulation for all providers"""
        if not self.providers:
            raise ValueError("No providers added to comparison")
        
        print("Running provider comparison...")
        
        for provider_name in self.providers:
            print(f"Simulating {provider_name}...")
            self.results[provider_name] = self.simulate_provider(provider_name)
        
        return self.results
    
    def calculate_summary_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """Calculate summary statistics for the comparison period"""
        if not self.results:
            raise ValueError("Run simulation first")
        
        summaries = []
        
        for provider_name, results_df in self.results.items():
            provider = self.providers[provider_name]
            
            # Filter by date range if specified
            if start_date or end_date:
                filtered_df = results_df.copy()
                if start_date:
                    filtered_df = filtered_df[filtered_df['timestamp'] >= start_date]
                if end_date:
                    filtered_df = filtered_df[filtered_df['timestamp'] <= end_date]
            else:
                filtered_df = results_df
            
            if len(filtered_df) == 0:
                continue
            
            # Calculate statistics properly by aggregating daily totals
            daily_totals = filtered_df.groupby('date').agg({
                'energy_cost': 'sum',
                'daily_charge': 'first',  # Same for all timesteps in a day
                'total_daily_cost': 'first'  # Same for all timesteps in a day
            }).reset_index()

            total_days = len(daily_totals)
            total_energy_cost = daily_totals['energy_cost'].sum()
            total_daily_charges = daily_totals['daily_charge'].sum()
            total_cost = total_energy_cost + total_daily_charges
            
            total_consumption = filtered_df['consumed_energy'].sum()
            total_generation = filtered_df['pv_energy'].sum()
            total_grid_purchase = filtered_df['grid_purchase'].sum()
            total_grid_sale = filtered_df['grid_sale'].sum()
            
            # Calculate purchases by time period
            period_purchases = {}
            period_sales = {}
            if provider.time_periods:
                for period in provider.time_periods:
                    period_mask = filtered_df['period_name'] == period.name
                    period_purchases[f'{period.name}_purchases_kwh'] = filtered_df[period_mask]['grid_purchase'].sum()
                    period_sales[f'{period.name}_sales_kwh'] = filtered_df[period_mask]['grid_sale'].sum()
            
            # For backward compatibility, still calculate peak/offpeak if available
            peak_purchases = period_purchases.get('peak_purchases_kwh', 0)
            offpeak_purchases = period_purchases.get('offpeak_purchases_kwh', 0)
            night_purchases = period_purchases.get('night_purchases_kwh', 0)
            
            # Calculate averages
            avg_daily_cost = total_cost / total_days if total_days > 0 else 0
            avg_cost_per_kwh = total_cost / total_consumption if total_consumption > 0 else 0
            
            summary = {
                'provider': provider_name,
                'data_start_date': self.data_start_date.strftime('%Y-%m-%d') if self.data_start_date else None,
                'data_end_date': self.data_end_date.strftime('%Y-%m-%d') if self.data_end_date else None,
                'total_data_days': self.total_days,
                'analysis_days': total_days,
                'interval_minutes': self.interval_minutes,
                'total_cost': total_cost,
                'total_energy_cost': total_energy_cost,
                'total_daily_charges': total_daily_charges,
                'avg_daily_cost': avg_daily_cost,
                'avg_cost_per_kwh_consumed': avg_cost_per_kwh,
                'total_consumption_kwh': total_consumption,
                'total_generation_kwh': total_generation,
                'total_grid_purchase_kwh': total_grid_purchase,
                'total_grid_sale_kwh': total_grid_sale,
                'peak_purchases_kwh': peak_purchases,
                'offpeak_purchases_kwh': offpeak_purchases,
                'night_purchases_kwh': night_purchases,
                'daily_charge': provider.daily_charge,
                'total_timesteps': len(filtered_df),
                'timesteps_per_day': len(filtered_df) / total_days if total_days > 0 else 0
            }
            
            # Add all period-specific purchases and sales
            summary.update(period_purchases)
            summary.update(period_sales)
            
            # Add pricing information for each period
            if provider.time_periods:
                for period in provider.time_periods:
                    summary[f'{period.name}_buy_price'] = period.buy_price
                    summary[f'{period.name}_buyback_price'] = period.buyback_price
            summaries.append(summary)
        
        summary_df = pd.DataFrame(summaries).sort_values('total_cost')
        return summary_df
    
    def plot_comparison(self, save_path: Optional[str] = None):
        """Create visualizations comparing providers"""
        if not self.results:
            raise ValueError("Run simulation first")
        
        # Calculate summary for plotting
        summary_df = self.calculate_summary_stats()
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Plot 1: Total cost comparison
        ax1 = axes[0, 0]
        bars = ax1.bar(summary_df['provider'], summary_df['total_cost'], 
                      color=sns.color_palette("viridis", len(summary_df)))
        ax1.set_title('Total Cost Comparison')
        ax1.set_ylabel('Total Cost ($)')
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.2f}',
                    ha='center', va='bottom')
        
        # Plot 2: Daily cost breakdown
        ax2 = axes[0, 1]
        width = 0.35
        x = np.arange(len(summary_df))
        
        bars1 = ax2.bar(x - width/2, summary_df['total_energy_cost'] / summary_df['analysis_days'],
                       width, label='Daily Energy Cost', alpha=0.8)
        bars2 = ax2.bar(x + width/2, summary_df['total_daily_charges'] / summary_df['analysis_days'],
                       width, label='Daily Fixed Charges', alpha=0.8)
        
        ax2.set_title('Daily Cost Breakdown')
        ax2.set_ylabel('Daily Cost ($)')
        ax2.set_xticks(x)
        ax2.set_xticklabels(summary_df['provider'], rotation=45)
        ax2.legend()
        
        # Plot 3: Cost per kWh consumed
        ax3 = axes[1, 0]
        bars = ax3.bar(summary_df['provider'], summary_df['avg_cost_per_kwh_consumed'], 
                      color=sns.color_palette("plasma", len(summary_df)))
        ax3.set_title('Average Cost per kWh Consumed')
        ax3.set_ylabel('Cost ($/kWh)')
        ax3.tick_params(axis='x', rotation=45)
        
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.3f}',
                    ha='center', va='bottom')
        
        # Plot 4: Peak vs Off-peak usage
        ax4 = axes[1, 1]
        x = np.arange(len(summary_df))
        
        bars1 = ax4.bar(x - width/2, summary_df['peak_purchases_kwh'], 
                       width, label='Peak Purchases', alpha=0.8, color='red')
        bars2 = ax4.bar(x + width/2, summary_df['offpeak_purchases_kwh'], 
                       width, label='Off-Peak Purchases', alpha=0.8, color='blue')
        
        ax4.set_title('Grid Purchases: Peak vs Off-Peak')
        ax4.set_ylabel('Energy (kWh)')
        ax4.set_xticks(x)
        ax4.set_xticklabels(summary_df['provider'], rotation=45)
        ax4.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Comparison plot saved to {save_path}")
        
        plt.show()
    
    def export_results(self, output_path: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """Export detailed results and summary to Excel"""
        if not self.results:
            raise ValueError("Run simulation first")
        
        # Calculate summary
        summary_df = self.calculate_summary_stats(start_date, end_date)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write summary sheet
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Write detailed results for each provider
            for provider_name, results_df in self.results.items():
                # Filter by date range if specified
                if start_date or end_date:
                    filtered_df = results_df.copy()
                    if start_date:
                        filtered_df = filtered_df[filtered_df['timestamp'] >= start_date]
                    if end_date:
                        filtered_df = filtered_df[filtered_df['timestamp'] <= end_date]
                else:
                    filtered_df = results_df
                
                # Write to sheet (truncate name if too long for Excel)
                sheet_name = provider_name[:31] if len(provider_name) > 31 else provider_name
                filtered_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"Results exported to {output_path}")

def create_sample_providers():
    """Create sample energy providers for demonstration"""
    providers = [
        EnergyProvider(
            name="PowerCorp Standard",
            daily_charge=1.20,
            gst_applicable=False,
            time_periods=[
                TimeOfUsePeriod(
                    name="peak",
                    buy_price=0.28,
                    buyback_price=0.08,
                    time_ranges=[{"start_hour": 7, "end_hour": 21, "days": [0, 1, 2, 3, 4, 5, 6]}]
                ),
                TimeOfUsePeriod(
                    name="offpeak",
                    buy_price=0.12,
                    buyback_price=0.08,
                    time_ranges=[
                        {"start_hour": 21, "end_hour": 24, "days": [0, 1, 2, 3, 4, 5, 6]},
                        {"start_hour": 0, "end_hour": 7, "days": [0, 1, 2, 3, 4, 5, 6]}
                    ]
                )
            ]
        ),
        EnergyProvider(
            name="GreenEnergy Plus",
            daily_charge=0.80,
            gst_applicable=True,
            time_periods=[
                TimeOfUsePeriod(
                    name="peak",
                    buy_price=0.32,
                    buyback_price=0.12,
                    time_ranges=[{"start_hour": 7, "end_hour": 21, "days": [0, 1, 2, 3, 4, 5, 6]}]
                ),
                TimeOfUsePeriod(
                    name="offpeak",
                    buy_price=0.08,
                    buyback_price=0.12,
                    time_ranges=[
                        {"start_hour": 21, "end_hour": 24, "days": [0, 1, 2, 3, 4, 5, 6]},
                        {"start_hour": 0, "end_hour": 7, "days": [0, 1, 2, 3, 4, 5, 6]}
                    ]
                )
            ]
        ),
        EnergyProvider(
            name="EcoUtility Premium",
            daily_charge=1.50,
            gst_applicable=False,
            time_periods=[
                TimeOfUsePeriod(
                    name="peak",
                    buy_price=0.26,
                    buyback_price=0.10,
                    time_ranges=[{"start_hour": 7, "end_hour": 21, "days": [0, 1, 2, 3, 4, 5, 6]}]
                ),
                TimeOfUsePeriod(
                    name="offpeak",
                    buy_price=0.15,
                    buyback_price=0.10,
                    time_ranges=[
                        {"start_hour": 21, "end_hour": 24, "days": [0, 1, 2, 3, 4, 5, 6]},
                        {"start_hour": 0, "end_hour": 7, "days": [0, 1, 2, 3, 4, 5, 6]}
                    ]
                )
            ]
        )
    ]
    return providers

def main():
    parser = argparse.ArgumentParser(description='Energy Provider Comparison Simulation')
    parser.add_argument('csv_file', help='Path to CSV file containing historical energy data')
    parser.add_argument('--providers-config', type=str, help='JSON file with provider configurations')
    parser.add_argument('--pv-column', type=str, help='Name of PV generation column')
    parser.add_argument('--consumption-column', type=str, help='Name of consumption column')
    parser.add_argument('--start-date', type=str, help='Start date for analysis (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date for analysis (YYYY-MM-DD)')
    parser.add_argument('--plot', action='store_true', help='Show comparison plots')
    parser.add_argument('--save-plot', type=str, help='Save plot to file')
    parser.add_argument('--export', type=str, help='Export results to Excel file')
    
    args = parser.parse_args()
    
    # Create comparison instance
    comparison = EnergyProviderComparison()
    
    # Load providers
    if args.providers_config:
        if not comparison.add_providers_from_config(args.providers_config):
            return
    else:
        # Use sample providers
        print("No provider config specified, using sample providers...")
        for provider in create_sample_providers():
            comparison.add_provider(provider)
    
    # Load data
    if not comparison.load_data(args.csv_file):
        return
    
    # Identify columns
    if not comparison.identify_columns(args.pv_column, args.consumption_column):
        return
    
    # Run comparison
    comparison.run_comparison()
    
    # Calculate and display summary
    summary_df = comparison.calculate_summary_stats(args.start_date, args.end_date)
    
    print("\n" + "="*80)
    print("ENERGY PROVIDER COMPARISON RESULTS")
    print("="*80)

    # Display data time span information
    if comparison.data_start_date and comparison.data_end_date:
        data_span_str = f"Data period: {comparison.data_start_date.strftime('%Y-%m-%d')} to {comparison.data_end_date.strftime('%Y-%m-%d')} ({comparison.total_days} days)"
        print(data_span_str)
        print("-" * len(data_span_str))

    # Display interval information
    if comparison.interval_minutes:
        interval_str = f"Data interval: {comparison.interval_minutes} minutes"
        if comparison.interval_minutes == 1.0:
            interval_desc = "(1-minute intervals)"
        elif comparison.interval_minutes == 5.0:
            interval_desc = "(5-minute intervals)"
        elif comparison.interval_minutes == 15.0:
            interval_desc = "(15-minute intervals)"
        elif comparison.interval_minutes == 30.0:
            interval_desc = "(30-minute intervals)"
        elif comparison.interval_minutes == 60.0:
            interval_desc = "(1-hour intervals)"
        else:
            interval_desc = f"({comparison.interval_minutes:.1f}-minute intervals)"

        print(f"{interval_str} {interval_desc}")
        print("-" * len(interval_str + " " + interval_desc))

    if args.start_date or args.end_date:
        period_str = f"Analysis period: {args.start_date or 'start'} to {args.end_date or 'end'}"
        print(period_str)
        print("-" * len(period_str))
    
    # Display summary table
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    display_cols = ['provider', 'data_start_date', 'data_end_date', 'total_data_days', 'analysis_days',
                   'total_cost', 'avg_daily_cost', 'avg_cost_per_kwh_consumed',
                   'total_consumption_kwh', 'total_generation_kwh', 'daily_charge']
    
    print("\nSUMMARY (sorted by total cost):")
    print(summary_df[display_cols].round(3).to_string(index=False))
    
    # Show savings vs most expensive
    if len(summary_df) > 1:
        most_expensive = summary_df['total_cost'].max()
        summary_df['savings_vs_most_expensive'] = most_expensive - summary_df['total_cost']
        summary_df['savings_percent'] = (summary_df['savings_vs_most_expensive'] / most_expensive) * 100
        
        print(f"\nPOTENTIAL SAVINGS vs most expensive ({summary_df.iloc[-1]['provider']}):")
        savings_cols = ['provider', 'total_cost', 'savings_vs_most_expensive', 'savings_percent']
        print(summary_df[savings_cols].round(2).to_string(index=False))
    
    # Export results if requested
    if args.export:
        comparison.export_results(args.export, args.start_date, args.end_date)
    
    # Show plots if requested
    if args.plot or args.save_plot:
        comparison.plot_comparison(args.save_plot)

if __name__ == "__main__":
    main()