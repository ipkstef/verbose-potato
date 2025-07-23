#!/usr/bin/env python3
"""
Test script for local development of the TCG Pricing Calculator
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        import pandas
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def create_test_files():
    """Create large test files for testing"""
    print("📁 Creating test files...")
    
    # Create a larger test file
    test_data = []
    headers = [
        "TCGplayer Id", "Product Line", "Set Name", "Product Name", "Title", 
        "Number", "Rarity", "Condition", "TCG Market Price", "TCG Direct Low",
        "TCG Low Price With Shipping", "TCG Low Price", "Total Quantity", 
        "Add to Quantity", "Photo URL"
    ]
    
    # Generate 100,000 rows of test data
    for i in range(100000):
        row = [
            str(10000 + i),  # TCGplayer Id
            "Magic: The Gathering",  # Product Line
            f"Test Set {i % 10}",  # Set Name
            f"Test Card {i}",  # Product Name
            f"Test Card {i}",  # Title
            f"{i:03d}",  # Number
            "Common" if i % 4 == 0 else "Uncommon" if i % 4 == 1 else "Rare" if i % 4 == 2 else "Mythic",  # Rarity
            "Near Mint",  # Condition
            str(round(1 + (i % 100) * 0.1, 2)),  # TCG Market Price
            str(round(0.8 + (i % 100) * 0.08, 2)),  # TCG Direct Low
            str(round(1.2 + (i % 100) * 0.12, 2)),  # TCG Low Price With Shipping
            str(round(0.9 + (i % 100) * 0.09, 2)),  # TCG Low Price
            str(i % 50 + 1),  # Total Quantity
            str(i % 10),  # Add to Quantity
            f"https://example.com/card{i}.jpg"  # Photo URL
        ]
        test_data.append(row)
    
    # Write test files
    with open('test_previous.csv', 'w', newline='', encoding='utf-8') as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(headers + ["Old Marketplace Price", "My Store Reserve Quantity", 
                                 "Old My Store Price", "Old Qty", "Base Price", 
                                 "TCG Marketplace Price", "My Store Price", 
                                 "Old Multiplier", "Multiplier", "Diff"])
        for row in test_data:
            writer.writerow(row + [str(round(1.1 + (int(row[0]) % 100) * 0.11, 2)), 
                               str(int(row[0]) % 5), str(round(1.2 + (int(row[0]) % 100) * 0.12, 2)),
                               str(int(row[0]) % 30), str(round(0.9 + (int(row[0]) % 100) * 0.09, 2)),
                               str(round(1.1 + (int(row[0]) % 100) * 0.11, 2)), str(round(1.2 + (int(row[0]) % 100) * 0.12, 2)),
                               "1.2", "1.2", "0.00"])
    
    with open('test_current.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in test_data:
            writer.writerow(row)
    
    print(f"✅ Created test files:")
    print(f"   - test_previous.csv ({os.path.getsize('test_previous.csv') / 1024 / 1024:.1f} MB)")
    print(f"   - test_current.csv ({os.path.getsize('test_current.csv') / 1024 / 1024:.1f} MB)")

def start_server():
    """Start the Flask development server"""
    print("🚀 Starting Flask development server...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Start the server
        subprocess.run([sys.executable, "app_large_files.py"])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")

def main():
    """Main test function"""
    print("🧪 TCG Pricing Calculator - Local Test")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Create test files if they don't exist
    if not os.path.exists('test_previous.csv') or not os.path.exists('test_current.csv'):
        create_test_files()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main() 