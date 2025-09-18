#!/usr/bin/env python3
"""
Solar Battery System Simulation
Analyzes the impact of adding battery storage to a solar energy system
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from datetime import datetime
import seaborn as sns

class SolarBatterySimulator:
    def __init__(self, 
                 battery_capacity=10.0,      # kWh
                 battery_efficiency=0.95,    # Round-trip efficiency (95%)
                 max_charge_rate=5.0,        # kW
                 max_discharge_rate=5.0,     # kW
                 grid_buy_price_peak=0.26,   # $/kWh during peak hours (7am-9pm)
                 grid_buy_price_offpeak=0.09, # $/kWh during off-peak hours
                 peak_start_hour=7,          # Peak pricing starts at 7am
                 peak_end_hour=21,           # Peak pricing ends at 9pm (21:00)
                 grid_sell_price=0.08,       # $/kWh (feed-in tariff)
                 battery_cost=8000,          # $ total system cost
                 battery_life_years=10):
        
        self.battery_capacity = battery_capacity
        self.battery_efficiency = battery_efficiency
        self.max_charge_rate = max_charge_rate
        self.max_discharge_rate = max_discharge_rate
        self.grid_buy_price_peak = grid_buy_price_peak
        self.grid_buy_price_offpeak = grid_buy_price_offpeak
        self.peak_start_hour = peak_start_hour
        self.peak_end_hour = peak_end_hour
        self.grid_sell_price = grid_sell_price
        self.battery_cost = battery_cost
        self.battery_life_years = battery_life_years
        
    def load_data(self, csv_path):
        """Load and prepare data from CSV file"""
        try:
            # Try to auto-detect the CSV structure
            df = pd.read_csv(csv_path)
            
            # Check if data is in pivoted format (timestamp, entity columns)
            if 'timestamp' in df.columns:
                self.data = df.copy()
                print(f"Loaded pivoted data with {len(df)} rows and columns: {list(df.columns)}")
            else:
                # Assume long format (entity_id, state, last_changed)
                df_pivot = df.pivot_table(
                    index='last_changed' if 'last_changed' in df.columns else 'timestamp',
                    columns='entity_id',
                    values='state',
                    aggfunc='mean'
                ).reset_index()
                
                # Rename index column to timestamp
                df_pivot.rename(columns={df_pivot.columns[0]: 'timestamp'}, inplace=True)
                self.data = df_pivot
                print(f"Pivoted long format data to {len(df_pivot)} rows and columns: {list(df_pivot.columns)}")
            
            # Ensure timestamp is datetime
            if 'timestamp' in self.data.columns:
                self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
                self.data = self.data.sort_values('timestamp').reset_index(drop=True)
            
            # Fill NaN values with 0
            self.data = self.data.fillna(0)
            
            return True
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return False

    def get_grid_buy_price(self, timestamp):
        """Get the grid buy price based on time of day"""
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        
        hour = timestamp.hour
        
        # Check if current hour is within peak pricing period
        if self.peak_start_hour <= hour < self.peak_end_hour:
            return self.grid_buy_price_peak
        else:
            return self.grid_buy_price_offpeak
    
    def identify_columns(self, pv_column=None, consumption_column=None):
        """Identify or set the PV generation and consumption columns"""
        columns = [col for col in self.data.columns if col != 'timestamp']
        
        print(f"Available columns: {columns}")
        
        if pv_column is None:
            # Try to auto-identify PV column
            pv_candidates = [col for col in columns if any(keyword in col.lower() 
                           for keyword in ['pv', 'solar', 'generation', 'gen'])]
            if pv_candidates:
                pv_column = pv_candidates[0]
                print(f"Auto-detected PV column: {pv_column}")
            else:
                print("Could not auto-detect PV column. Please specify manually.")
                return False
        
        if consumption_column is None:
            # Try to auto-identify consumption column
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
        
        # Ensure columns exist
        if pv_column not in self.data.columns:
            print(f"PV column '{pv_column}' not found in data")
            return False
        if consumption_column not in self.data.columns:
            print(f"Consumption column '{consumption_column}' not found in data")
            return False
            
        return True
    
    def simulate(self, initial_soc=0.5):
        """Run the battery simulation"""
        if not hasattr(self, 'pv_column') or not hasattr(self, 'consumption_column'):
            raise ValueError("PV and consumption columns not identified. Run identify_columns() first.")
        
        # Initialize results
        results = []
        battery_level = self.battery_capacity * initial_soc  # Start at specified SOC
        
        for idx, row in self.data.iterrows():
            pv_power = row[self.pv_column]
            consumed_power = row[self.consumption_column]
            net_power = pv_power - consumed_power  # Positive = excess, Negative = deficit
            
            # Get current timestamp and grid buy price
            current_timestamp = row['timestamp'] if 'timestamp' in row else pd.Timestamp.now()
            current_buy_price = self.get_grid_buy_price(current_timestamp)
            
            # Initialize values for this timestep
            grid_purchase = 0
            grid_sale = 0
            battery_charge = 0
            battery_discharge = 0
            
            if net_power > 0:
                # Excess power available - charge battery first, then sell to grid
                # Calculate maximum possible charge (limited by power, charge rate, and capacity)
                max_charge = min(
                    net_power,
                    self.max_charge_rate,
                    (self.battery_capacity - battery_level) / self.battery_efficiency
                )
                
                battery_charge = max_charge
                battery_level = min(self.battery_capacity, 
                                  battery_level + (battery_charge * self.battery_efficiency))
                
                # Sell remaining excess to grid
                remaining_excess = net_power - battery_charge
                if remaining_excess > 0:
                    grid_sale = remaining_excess
                    
            elif net_power < 0:
                # Power deficit - discharge battery first, then buy from grid
                power_needed = abs(net_power)
                
                # Calculate maximum possible discharge
                max_discharge = min(
                    power_needed,
                    self.max_discharge_rate,
                    battery_level * self.battery_efficiency
                )
                
                battery_discharge = max_discharge
                battery_level = max(0, battery_level - (battery_discharge / self.battery_efficiency))
                
                # Buy remaining deficit from grid
                remaining_deficit = power_needed - battery_discharge
                if remaining_deficit > 0:
                    grid_purchase = remaining_deficit
            
            # Calculate costs for this timestep using time-of-use pricing
            timestep_cost = grid_purchase * current_buy_price - grid_sale * self.grid_sell_price
            
            # Store results
            result = {
                'timestamp': row['timestamp'] if 'timestamp' in row else idx,
                'pv_power': pv_power,
                'consumed_power': consumed_power,
                'net_power': net_power,
                'battery_level': battery_level,
                'battery_soc': battery_level / self.battery_capacity,
                'battery_charge': battery_charge,
                'battery_discharge': battery_discharge,
                'grid_purchase': grid_purchase,
                'grid_sale': grid_sale,
                'grid_buy_price': current_buy_price,
                'cost': timestep_cost
            }
            results.append(result)
        
        self.results_df = pd.DataFrame(results)
        return self.results_df
    
    def simulate_without_battery(self):
        """Simulate the system without battery for comparison"""
        results_no_battery = []
        
        for idx, row in self.data.iterrows():
            pv_power = row[self.pv_column]
            consumed_power = row[self.consumption_column]
            net_power = pv_power - consumed_power
            
            # Get current timestamp and grid buy price
            current_timestamp = row['timestamp'] if 'timestamp' in row else pd.Timestamp.now()
            current_buy_price = self.get_grid_buy_price(current_timestamp)
            
            # Without battery: buy all deficit, sell all excess
            grid_purchase = max(0, -net_power)
            grid_sale = max(0, net_power)
            cost = grid_purchase * current_buy_price - grid_sale * self.grid_sell_price
            
            result = {
                'timestamp': row['timestamp'] if 'timestamp' in row else idx,
                'pv_power': pv_power,
                'consumed_power': consumed_power,
                'net_power': net_power,
                'grid_purchase': grid_purchase,
                'grid_sale': grid_sale,
                'grid_buy_price': current_buy_price,
                'cost': cost
            }
            results_no_battery.append(result)
        
        self.results_no_battery_df = pd.DataFrame(results_no_battery)
        return self.results_no_battery_df
    
    def calculate_economics(self):
        """Calculate the economic impact of the battery system"""
        if not hasattr(self, 'results_df') or not hasattr(self, 'results_no_battery_df'):
            raise ValueError("Run simulations first")
        
        # Daily totals
        total_cost_with_battery = self.results_df['cost'].sum()
        total_cost_without_battery = self.results_no_battery_df['cost'].sum()
        daily_savings = total_cost_without_battery - total_cost_with_battery
        
        # Annual projections (assuming this is representative data)
        annual_savings = daily_savings * 365
        payback_period = self.battery_cost / annual_savings if annual_savings > 0 else float('inf')
        
        # Battery utilization
        total_energy_charged = self.results_df['battery_charge'].sum()
        total_energy_discharged = self.results_df['battery_discharge'].sum()
        round_trip_efficiency = total_energy_discharged / total_energy_charged if total_energy_charged > 0 else 0
        
        # Peak vs off-peak analysis
        peak_purchases_with = self.results_df[self.results_df['grid_buy_price'] == self.grid_buy_price_peak]['grid_purchase'].sum()
        offpeak_purchases_with = self.results_df[self.results_df['grid_buy_price'] == self.grid_buy_price_offpeak]['grid_purchase'].sum()
        peak_purchases_without = self.results_no_battery_df[self.results_no_battery_df['grid_buy_price'] == self.grid_buy_price_peak]['grid_purchase'].sum()
        offpeak_purchases_without = self.results_no_battery_df[self.results_no_battery_df['grid_buy_price'] == self.grid_buy_price_offpeak]['grid_purchase'].sum()
        
        economics = {
            'daily_cost_with_battery': total_cost_with_battery,
            'daily_cost_without_battery': total_cost_without_battery,
            'daily_savings': daily_savings,
            'annual_savings': annual_savings,
            'battery_cost': self.battery_cost,
            'payback_period_years': payback_period,
            'total_energy_charged': total_energy_charged,
            'total_energy_discharged': total_energy_discharged,
            'actual_round_trip_efficiency': round_trip_efficiency,
            'battery_utilization_cycles': total_energy_discharged / self.battery_capacity if self.battery_capacity > 0 else 0,
            'peak_purchases_with_battery': peak_purchases_with,
            'offpeak_purchases_with_battery': offpeak_purchases_with,
            'peak_purchases_without_battery': peak_purchases_without,
            'offpeak_purchases_without_battery': offpeak_purchases_without,
            'peak_purchase_reduction': peak_purchases_without - peak_purchases_with,
            'offpeak_purchase_increase': offpeak_purchases_with - offpeak_purchases_without
        }
        
        return economics
    
    def plot_results(self, save_path=None):
        """Create visualization of the simulation results"""
        if not hasattr(self, 'results_df'):
            raise ValueError("Run simulation first")
        
        fig, axes = plt.subplots(4, 1, figsize=(15, 16))
        
        # Plot 1: Power flows
        ax1 = axes[0]
        ax1.plot(self.results_df.index, self.results_df['pv_power'], label='PV Generation', color='orange')
        ax1.plot(self.results_df.index, self.results_df['consumed_power'], label='Consumption', color='red')
        ax1.plot(self.results_df.index, self.results_df['net_power'], label='Net Power', color='blue', alpha=0.7)
        ax1.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax1.set_ylabel('Power (kW)')
        ax1.set_title('Power Generation and Consumption')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Battery operation
        ax2 = axes[1]
        ax2_twin = ax2.twinx()
        
        # Battery level
        ax2.plot(self.results_df.index, self.results_df['battery_soc'] * 100, 
                label='Battery SOC', color='green', linewidth=2)
        ax2.set_ylabel('Battery SOC (%)', color='green')
        ax2.set_ylim(0, 100)
        
        # Battery charge/discharge
        charge_bars = ax2_twin.bar(self.results_df.index, self.results_df['battery_charge'], 
                                  alpha=0.6, color='blue', label='Charge', width=0.8)
        discharge_bars = ax2_twin.bar(self.results_df.index, -self.results_df['battery_discharge'], 
                                     alpha=0.6, color='red', label='Discharge', width=0.8)
        ax2_twin.set_ylabel('Battery Power (kW)', color='blue')
        ax2_twin.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
        ax2.set_title('Battery Operation')
        ax2.grid(True, alpha=0.3)
        
        # Combined legend
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2_twin.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        # Plot 3: Grid interaction and costs
        ax3 = axes[2]
        ax3_twin = ax3.twinx()
        
        # Grid purchases/sales
        purchase_bars = ax3.bar(self.results_df.index, self.results_df['grid_purchase'], 
                               alpha=0.6, color='red', label='Grid Purchase', width=0.8)
        sale_bars = ax3.bar(self.results_df.index, -self.results_df['grid_sale'], 
                           alpha=0.6, color='green', label='Grid Sale', width=0.8)
        ax3.set_ylabel('Grid Power (kW)')
        ax3.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
        # Cumulative cost
        cumulative_cost = self.results_df['cost'].cumsum()
        ax3_twin.plot(self.results_df.index, cumulative_cost, 
                     color='purple', linewidth=2, label='Cumulative Cost')
        ax3_twin.set_ylabel('Cumulative Cost ($)', color='purple')
        
        ax3.set_title('Grid Interaction and Costs')
        ax3.grid(True, alpha=0.3)
        
        # Combined legend
        lines1, labels1 = ax3.get_legend_handles_labels()
        lines2, labels2 = ax3_twin.get_legend_handles_labels()
        ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        # Plot 4: Time-of-use pricing visualization
        ax4 = axes[3]
        
        # Color-code grid purchases by price
        peak_mask = self.results_df['grid_buy_price'] == self.grid_buy_price_peak
        offpeak_mask = self.results_df['grid_buy_price'] == self.grid_buy_price_offpeak
        
        ax4.bar(self.results_df.index[peak_mask], self.results_df['grid_purchase'][peak_mask], 
               alpha=0.7, color='red', label=f'Peak Purchase (${self.grid_buy_price_peak:.3f})', width=0.8)
        ax4.bar(self.results_df.index[offpeak_mask], self.results_df['grid_purchase'][offpeak_mask], 
               alpha=0.7, color='blue', label=f'Off-Peak Purchase (${self.grid_buy_price_offpeak:.3f})', width=0.8)
        
        ax4.set_xlabel('Time Step')
        ax4.set_ylabel('Grid Purchases (kW)')
        ax4.set_title('Time-of-Use Grid Purchases')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        
        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Solar Battery System Simulation')
    parser.add_argument('csv_file', help='Path to CSV file containing solar data')
    parser.add_argument('--battery-capacity', type=float, default=10.0, help='Battery capacity in kWh (default: 10)')
    parser.add_argument('--battery-efficiency', type=float, default=0.95, help='Round-trip efficiency (default: 0.95)')
    parser.add_argument('--charge-rate', type=float, default=5.0, help='Max charge rate in kW (default: 5)')
    parser.add_argument('--discharge-rate', type=float, default=5.0, help='Max discharge rate in kW (default: 5)')
    parser.add_argument('--buy-price-peak', type=float, default=0.26, help='Grid buy price during peak hours $/kWh (default: 0.26)')
    parser.add_argument('--buy-price-offpeak', type=float, default=0.09, help='Grid buy price during off-peak hours $/kWh (default: 0.09)')
    parser.add_argument('--peak-start', type=int, default=7, help='Peak pricing start hour (default: 7)')
    parser.add_argument('--peak-end', type=int, default=21, help='Peak pricing end hour (default: 21)')
    parser.add_argument('--sell-price', type=float, default=0.08, help='Grid sell price $/kWh (default: 0.08)')
    parser.add_argument('--battery-cost', type=float, default=8000, help='Battery system cost $ (default: 8000)')
    parser.add_argument('--pv-column', type=str, help='Name of PV generation column')
    parser.add_argument('--consumption-column', type=str, help='Name of consumption column')
    parser.add_argument('--plot', action='store_true', help='Show plots')
    parser.add_argument('--save-plot', type=str, help='Save plot to file')
    
    args = parser.parse_args()
    
    # Create simulator
    simulator = SolarBatterySimulator(
        battery_capacity=args.battery_capacity,
        battery_efficiency=args.battery_efficiency,
        max_charge_rate=args.charge_rate,
        max_discharge_rate=args.discharge_rate,
        grid_buy_price_peak=args.buy_price_peak,
        grid_buy_price_offpeak=args.buy_price_offpeak,
        peak_start_hour=args.peak_start,
        peak_end_hour=args.peak_end,
        grid_sell_price=args.sell_price,
        battery_cost=args.battery_cost
    )
    
    # Load data
    if not simulator.load_data(args.csv_file):
        return
    
    # Identify columns
    if not simulator.identify_columns(args.pv_column, args.consumption_column):
        return
    
    # Run simulations
    print("Running battery simulation...")
    simulator.simulate()
    
    print("Running baseline simulation (no battery)...")
    simulator.simulate_without_battery()
    
    # Calculate economics
    economics = simulator.calculate_economics()
    
    # Print results
    print("\n" + "="*50)
    print("SIMULATION RESULTS")
    print("="*50)
    print(f"Battery Capacity: {args.battery_capacity:.1f} kWh")
    print(f"Max Charge/Discharge Rate: {args.charge_rate:.1f} / {args.discharge_rate:.1f} kW")
    print(f"Grid Buy Price (Peak): ${args.buy_price_peak:.3f} per kWh ({args.peak_start}:00-{args.peak_end}:00)")
    print(f"Grid Buy Price (Off-Peak): ${args.buy_price_offpeak:.3f} per kWh")
    print(f"Grid Sell Price: ${args.sell_price:.3f} per kWh")
    print()
    print("DAILY ECONOMICS:")
    print(f"  Cost without battery: ${economics['daily_cost_without_battery']:.2f}")
    print(f"  Cost with battery:    ${economics['daily_cost_with_battery']:.2f}")
    print(f"  Daily savings:        ${economics['daily_savings']:.2f}")
    print()
    print("ANNUAL PROJECTIONS:")
    print(f"  Annual savings:       ${economics['annual_savings']:.2f}")
    print(f"  Battery system cost:  ${economics['battery_cost']:.2f}")
    print(f"  Payback period:       {economics['payback_period_years']:.1f} years")
    print()
    print("BATTERY UTILIZATION:")
    print(f"  Energy charged:       {economics['total_energy_charged']:.2f} kWh")
    print(f"  Energy discharged:    {economics['total_energy_discharged']:.2f} kWh")
    print(f"  Round-trip efficiency: {economics['actual_round_trip_efficiency']:.1%}")
    print(f"  Daily cycles:         {economics['battery_utilization_cycles']:.2f}")
    print()
    print("TIME-OF-USE IMPACT:")
    print(f"  Peak purchases without battery:   {economics['peak_purchases_without_battery']:.2f} kWh")
    print(f"  Peak purchases with battery:      {economics['peak_purchases_with_battery']:.2f} kWh")
    print(f"  Peak purchase reduction:          {economics['peak_purchase_reduction']:.2f} kWh")
    print(f"  Off-peak purchase increase:       {economics['offpeak_purchase_increase']:.2f} kWh")
    
    # Show plots if requested
    if args.plot or args.save_plot:
        simulator.plot_results(args.save_plot)

if __name__ == "__main__":
    main()