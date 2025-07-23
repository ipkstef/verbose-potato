import pandas as pd
import os
import io
import base64
import tempfile
import json
from flask import Flask, render_template, request, jsonify, Response, stream_template, send_file
from werkzeug.utils import secure_filename
import csv
from datetime import datetime
import threading
import queue

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global processing queue
processing_queue = queue.Queue()
results_cache = {}

def process_csv_chunked(file_path, file_type):
    """
    Process large CSV files in chunks to handle 300MB+ files
    """
    try:
        # Read CSV in chunks
        chunk_size = 10000  # Process 10k rows at a time
        chunks = []
        
        print(f"Processing {file_type} file: {file_path}")
        
        for chunk in pd.read_csv(file_path, chunksize=chunk_size, encoding='utf-8-sig'):
            chunks.append(chunk)
            print(f"Processed chunk of {len(chunk)} rows")
        
        # Combine all chunks
        df = pd.concat(chunks, ignore_index=True)
        print(f"Total rows in {file_type}: {len(df)}")
        
        return df, None
        
    except Exception as e:
        return None, str(e)

def process_pricing_data_large(previous_file_path, current_file_path):
    """
    Process large pricing data files with memory optimization
    """
    try:
        print("Starting large file processing...")
        
        # Process previous file
        previous, error = process_csv_chunked(previous_file_path, "previous")
        if error:
            return None, f"Error processing previous file: {error}"
        
        # Process current file
        current, error = process_csv_chunked(current_file_path, "current")
        if error:
            return None, f"Error processing current file: {error}"
        
        print(f"Previous file: {len(previous)} rows")
        print(f"Current file: {len(current)} rows")
        
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

        # Rename columns in current file
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

        print("Merging data...")
        # Merge data
        merged = pd.merge(
            current,
            previous[["TCGplayer Id", "Old Multiplier"]],
            on="TCGplayer Id",
            how="left"
        )

        # Fill missing Old Multiplier with default value
        merged["Old Multiplier"] = merged["Old Multiplier"].fillna(1.2)

        print("Calculating base prices...")
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

        print("Calculating multipliers...")
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

        print("Calculating store prices...")
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

        print("Calculating differences...")
        # Calculate Diff
        merged["Old My Store Price"] = merged["Old My Store Price"].fillna(0.0)
        merged["Diff"] = merged["My Store Price"] - merged["Old My Store Price"]

        print("Processing complete!")
        return merged, None
        
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    """Main page with file upload interface"""
    return render_template('index_large_files.html')

@app.route('/process_large', methods=['POST'])
def process_large_files():
    """Process large CSV files with progress updates"""
    try:
        # Check if files were uploaded
        if 'previous_file' not in request.files or 'current_file' not in request.files:
            return jsonify({'error': 'Both previous.csv and current.csv files are required'}), 400
        
        previous_file = request.files['previous_file']
        current_file = request.files['current_file']
        
        # Check if files are selected
        if previous_file.filename == '' or current_file.filename == '':
            return jsonify({'error': 'Please select both files'}), 400
        
        # Save files to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_previous:
            previous_file.save(temp_previous.name)
            previous_path = temp_previous.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_current:
            current_file.save(temp_current.name)
            current_path = temp_current.name
        
        # Process the files
        merged_df, error = process_pricing_data_large(previous_path, current_path)
        
        # Clean up temporary files
        try:
            os.unlink(previous_path)
            os.unlink(current_path)
        except:
            pass
        
        if error:
            return jsonify({'error': f'Processing error: {error}'}), 500
        
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
        
        # Save to temporary file for download
        output_filename = f"updated_pricing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        merged_df.to_csv(output_path, index=False)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'filename': output_filename,
            'file_size_mb': round(os.path.getsize(output_path) / (1024 * 1024), 2)
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download the processed CSV file"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True) 