import pandas as pd
import os
import io
import base64
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile
import zipfile
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- PRICING LOGIC FUNCTIONS ---
def process_pricing_data(previous_file, current_file):
    """
    Process pricing data from uploaded CSV files
    Returns processed DataFrame and any errors
    """
    try:
        # Load previous.csv
        previous = pd.read_csv(
            previous_file,
            encoding='utf-8-sig',
            on_bad_lines='skip'
        )
        
        # Define required columns for previous.csv
        required_previous_columns = {
            "TCGplayer Id": 'Int64',
            "Product Line": 'string',
            "Set Name": 'string',
            "Product Name": 'string',
            "Title": 'string',
            "Number": 'string',
            "Rarity": 'string',
            "Condition": 'string',
            "TCG Market Price": 'float64',
            "TCG Direct Low": 'float64',
            "TCG Low Price With Shipping": 'float64',
            "TCG Low Price": 'float64',
            "Total Quantity": 'Int64',
            "Add to Quantity": 'Int64',
            "Old Marketplace Price": 'float64',
            "My Store Reserve Quantity": 'Int64',
            "Old My Store Price": 'float64',
            "Photo URL": 'string',
            "Old Qty": 'Int64',
            "Base Price": 'float64',
            "TCG Marketplace Price": 'float64',
            "My Store Price": 'float64',
            "Old Multiplier": 'float64',
            "Multiplier": 'float64',
            "Diff": 'float64'
        }

        # Add missing columns with default values
        for col, dtype in required_previous_columns.items():
            if col not in previous.columns:
                if dtype == 'float64':
                    previous[col] = float('nan')
                elif dtype == 'Int64':
                    previous[col] = pd.NA
                else:
                    previous[col] = ''

        # Convert column types
        for col, dtype in required_previous_columns.items():
            try:
                if dtype == 'Int64':
                    previous[col] = pd.to_numeric(previous[col], errors='coerce').astype('Int64')
                elif dtype == 'float64':
                    previous[col] = pd.to_numeric(previous[col], errors='coerce')
                elif dtype == 'string':
                    previous[col] = previous[col].astype(str)
            except Exception:
                previous[col] = float('nan')

        # Load current.csv
        current = pd.read_csv(
            current_file,
            encoding='utf-8-sig',
            on_bad_lines='skip'
        )

        # Rename columns
        if "My Store Price" in current.columns:
            current = current.rename(columns={"My Store Price": "Old My Store Price"})
        else:
            current["Old My Store Price"] = float('nan')

        if "TCG Marketplace Price" in current.columns:
            current = current.rename(columns={"TCG Marketplace Price": "Old Marketplace Price"})
        else:
            current["Old Marketplace Price"] = float('nan')

        # Filter rows
        current = current[current["Condition"] != "Unopened"]
        current = current[current["TCG Market Price"].notna()]

        # Ensure TCGplayer Id is numeric
        current["TCGplayer Id"] = pd.to_numeric(current["TCGplayer Id"], errors='coerce').astype('Int64')

        # Merge data
        merged = pd.merge(
            current,
            previous[["TCGplayer Id", "Old Multiplier"]],
            on="TCGplayer Id",
            how="left"
        )

        # Fill missing Old Multiplier with default value
        merged["Old Multiplier"] = merged["Old Multiplier"].fillna(1.2)

        # Calculate Base Price
        def calculate_base_price(row):
            market = row["TCG Market Price"]
            low = row["TCG Low Price"]
            if pd.notna(market) and pd.notna(low):
                return round(min(market, low), 2)
            elif pd.notna(low):
                return round(low, 2)
            elif pd.notna(market):
                return round(market, 2)
            else:
                return 50000.00

        merged["Base Price"] = merged.apply(calculate_base_price, axis=1)

        # Calculate Multiplier
        def calculate_multiplier(row):
            old_qty = row.get("Old Qty", 0)
            new_qty = row.get("Total Quantity", 0)
            old_mult = row.get("Old Multiplier", 1.2)

            if old_qty == 0:
                return 1.2
            elif old_qty > 0 and new_qty == 0:
                return 1.2
            elif old_qty < new_qty:
                return round(old_mult + 0.01, 2)
            elif old_mult - 0.05 > 1:
                return round(old_mult - 0.05, 2)
            else:
                return round(old_mult - 0.01, 2)

        merged["Multiplier"] = merged.apply(calculate_multiplier, axis=1)

        # Calculate My Store Price
        def calculate_store_price(row):
            market_price = row["TCG Market Price"]
            base = row["Base Price"]
            mult = row["Multiplier"]
            qty = row["Total Quantity"]

            raw_price = round(market_price if pd.notna(market_price) else base * mult, 2)
            bump = 0.25
            if qty >= 40:
                bump = 0.05
            elif qty >= 20:
                bump = 0.15
            return raw_price + max(0, bump - raw_price)

        merged["My Store Price"] = merged.apply(calculate_store_price, axis=1)

        # Calculate Diff
        merged["Old My Store Price"] = merged["Old My Store Price"].fillna(0.0)
        merged["Diff"] = merged["My Store Price"] - merged["Old My Store Price"]

        return merged, None
        
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    """Main page with file upload interface"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_files():
    """Process uploaded CSV files and return results"""
    try:
        # Check if files were uploaded
        if 'previous_file' not in request.files or 'current_file' not in request.files:
            return jsonify({'error': 'Both previous.csv and current.csv files are required'}), 400
        
        previous_file = request.files['previous_file']
        current_file = request.files['current_file']
        
        # Check if files are selected
        if previous_file.filename == '' or current_file.filename == '':
            return jsonify({'error': 'Please select both files'}), 400
        
        # Process the files
        merged_df, error = process_pricing_data(previous_file, current_file)
        
        if error:
            return jsonify({'error': f'Processing error: {error}'}), 500
        
        # Convert to CSV string
        output = io.StringIO()
        merged_df.to_csv(output, index=False)
        csv_content = output.getvalue()
        
        # Create summary statistics
        summary = {
            'total_items': len(merged_df),
            'avg_market_price': round(merged_df['TCG Market Price'].mean(), 2),
            'avg_store_price': round(merged_df['My Store Price'].mean(), 2),
            'total_value': round(merged_df['My Store Price'].sum(), 2),
            'price_changes': {
                'increased': len(merged_df[merged_df['Diff'] > 0]),
                'decreased': len(merged_df[merged_df['Diff'] < 0]),
                'unchanged': len(merged_df[merged_df['Diff'] == 0])
            }
        }
        
        # Encode CSV content for download
        csv_b64 = base64.b64encode(csv_content.encode()).decode()
        
        return jsonify({
            'success': True,
            'summary': summary,
            'csv_data': csv_b64,
            'filename': f'updated_pricing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download the processed CSV file"""
    try:
        # This would need to be implemented with proper file storage
        # For now, we'll return a simple response
        return jsonify({'message': 'Download functionality would be implemented here'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 