#!/usr/bin/env python3
"""
Test script to verify 3-tier time-of-use pricing logic
"""

import pandas as pd
from datetime import datetime, timedelta
from energy_provider_comparison import EnergyProvider

def test_3tier_pricing():
    """Test the 3-tier pricing logic"""
    
    # Create a 3-tier provider
    provider = EnergyProvider(
        name="Test 3-Tier",
        peak_buy_price=0.35,
        offpeak_buy_price=0.18,
        night_buy_price=0.12,
        peak_buyback_price=0.10,
        offpeak_buyback_price=0.08,
        night_buyback_price=0.05,
        daily_charge=1.50
    )
    
    # Test times for each period
    test_cases = [
        # Monday (weekday) - different hours
        (datetime(2024, 1, 1, 6, 0), "night"),    # 6am Monday - night
        (datetime(2024, 1, 1, 8, 0), "peak"),    # 8am Monday - peak (7-11am)
        (datetime(2024, 1, 1, 12, 0), "offpeak"), # 12pm Monday - offpeak (11am-5pm)
        (datetime(2024, 1, 1, 18, 0), "peak"),   # 6pm Monday - peak (5-9pm)
        (datetime(2024, 1, 1, 22, 0), "offpeak"), # 10pm Monday - offpeak (9-11pm)
        (datetime(2024, 1, 1, 23, 30), "night"), # 11:30pm Monday - night
        (datetime(2024, 1, 2, 2, 0), "night"),   # 2am Tuesday - night
        
        # Saturday (weekend)
        (datetime(2024, 1, 6, 8, 0), "offpeak"),  # 8am Saturday - offpeak (7am-11pm weekend)
        (datetime(2024, 1, 6, 15, 0), "offpeak"), # 3pm Saturday - offpeak
        (datetime(2024, 1, 6, 23, 30), "night"), # 11:30pm Saturday - night
        
        # Sunday (weekend)
        (datetime(2024, 1, 7, 10, 0), "offpeak"), # 10am Sunday - offpeak
        (datetime(2024, 1, 7, 23, 30), "night"), # 11:30pm Sunday - night
    ]
    
    print("Testing 3-Tier Pricing Logic:")
    print("=" * 60)
    print(f"Peak: 7-11am & 5-9pm weekdays (${provider.time_periods[0].buy_price:.3f} buy, ${provider.time_periods[0].buyback_price:.3f} buyback)")
    print(f"Off-peak: 11am-5pm & 9-11pm weekdays, 7am-11pm weekends (${provider.time_periods[1].buy_price:.3f} buy, ${provider.time_periods[1].buyback_price:.3f} buyback)")
    print(f"Night: 11pm-7am every day (${provider.time_periods[2].buy_price:.3f} buy, ${provider.time_periods[2].buyback_price:.3f} buyback)")
    print("-" * 60)
    
    all_passed = True
    
    for timestamp, expected_period in test_cases:
        ts = pd.Timestamp(timestamp)
        buy_price, buyback_price, period_name = provider.get_pricing(ts)
        
        day_name = ts.strftime("%A")
        time_str = ts.strftime("%I:%M %p")
        
        status = "✓" if period_name == expected_period else "✗"
        if period_name != expected_period:
            all_passed = False
        
        print(f"{status} {day_name} {time_str}: {period_name:8} (expected: {expected_period:8}) - ${buy_price:.3f}/${buyback_price:.3f}")
    
    print("-" * 60)
    if all_passed:
        print("✓ All tests passed! 3-tier pricing logic is working correctly.")
    else:
        print("✗ Some tests failed. Please check the pricing logic.")
    
    return all_passed

def test_legacy_2tier_pricing():
    """Test that legacy 2-tier pricing still works"""
    
    # Create a legacy 2-tier provider
    provider = EnergyProvider(
        name="Legacy 2-Tier",
        peak_buy_price=0.26,
        offpeak_buy_price=0.09,
        solar_buyback_price=0.12,
        daily_charge=2.20
    )
    
    test_cases = [
        (datetime(2024, 1, 1, 8, 0), "peak"),     # 8am Monday - peak
        (datetime(2024, 1, 1, 22, 0), "offpeak"), # 10pm Monday - offpeak
        (datetime(2024, 1, 6, 15, 0), "peak"),    # 3pm Saturday - peak (7am-9pm every day)
        (datetime(2024, 1, 6, 22, 0), "offpeak"), # 10pm Saturday - offpeak
        (datetime(2024, 1, 7, 8, 0), "peak"),     # 8am Sunday - peak
        (datetime(2024, 1, 7, 23, 0), "offpeak"), # 11pm Sunday - offpeak
    ]
    
    print("\nTesting Legacy 2-Tier Pricing:")
    print("=" * 60)
    
    all_passed = True
    
    for timestamp, expected_period in test_cases:
        ts = pd.Timestamp(timestamp)
        buy_price, buyback_price, period_name = provider.get_pricing(ts)
        
        day_name = ts.strftime("%A")
        time_str = ts.strftime("%I:%M %p")
        
        status = "✓" if period_name == expected_period else "✗"
        if period_name != expected_period:
            all_passed = False
        
        print(f"{status} {day_name} {time_str}: {period_name:8} (expected: {expected_period:8}) - ${buy_price:.3f}/${buyback_price:.3f}")
    
    print("-" * 60)
    if all_passed:
        print("✓ Legacy 2-tier pricing tests passed!")
    else:
        print("✗ Legacy 2-tier pricing tests failed.")
    
    return all_passed

if __name__ == "__main__":
    test_3tier = test_3tier_pricing()
    test_2tier = test_legacy_2tier_pricing()
    
    if test_3tier and test_2tier:
        print("\n🎉 All pricing tests passed!")
    else:
        print("\n❌ Some tests failed - please review the implementation.")