# TCG Pricing Calculator Web App

A modern web application for automated pricing calculation of trading card games. This app processes CSV files containing TCG market data and calculates optimal store pricing based on market conditions and inventory levels.

## Features

- 📊 **Automated Pricing Logic**: Calculates store prices based on market data and inventory levels
- 📈 **Real-time Processing**: Upload CSV files and get instant results
- 📱 **Responsive Design**: Works perfectly on desktop and mobile devices
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations
- 📥 **Download Results**: Export processed data as CSV files
- 📊 **Summary Statistics**: View key metrics and price change analysis

## How It Works

The application processes two CSV files:

1. **previous.csv**: Contains historical pricing data and inventory levels
2. **current.csv**: Contains current market data and pricing information

The pricing algorithm:
- Calculates base prices from market and low prices
- Adjusts multipliers based on inventory changes
- Applies quantity-based pricing bumps
- Generates summary statistics and downloadable results

## Local Development

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd tcg-pricing-calculator
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Flask development server**:
   ```bash
   python app.py
   ```

4. **Open your browser** and navigate to `http://localhost:5000`

### Testing

To test the application, you'll need sample CSV files with the following columns:

**previous.csv** should contain:
- TCGplayer Id
- Product Line
- Set Name
- Product Name
- Title
- Number
- Rarity
- Condition
- TCG Market Price
- TCG Direct Low
- TCG Low Price With Shipping
- TCG Low Price
- Total Quantity
- Add to Quantity
- Old Marketplace Price
- My Store Reserve Quantity
- Old My Store Price
- Photo URL
- Old Qty
- Base Price
- TCG Marketplace Price
- My Store Price
- Old Multiplier
- Multiplier
- Diff

**current.csv** should contain:
- TCGplayer Id
- Product Line
- Set Name
- Product Name
- Title
- Number
- Rarity
- Condition
- TCG Market Price
- TCG Direct Low
- TCG Low Price With Shipping
- TCG Low Price
- Total Quantity
- Add to Quantity
- Photo URL

## Deployment to Cloudflare Pages

### Option 1: Using Wrangler CLI

1. **Install Wrangler**:
   ```bash
   npm install -g wrangler
   ```

2. **Login to Cloudflare**:
   ```bash
   wrangler login
   ```

3. **Deploy the application**:
   ```bash
   wrangler pages deploy public --project-name tcg-pricing-calculator
   ```

### Option 2: Using Cloudflare Dashboard

1. **Push your code to GitHub**

2. **Connect to Cloudflare Pages**:
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Navigate to Pages
   - Click "Create a project"
   - Choose "Connect to Git"
   - Select your repository

3. **Configure build settings**:
   - **Build command**: Leave empty (static site)
   - **Build output directory**: `public`
   - **Root directory**: Leave as default

4. **Deploy**: Click "Save and Deploy"

### Environment Variables

No environment variables are required for this application.

## Project Structure

```
tcg-pricing-calculator/
├── app.py                 # Flask application (local development)
├── requirements.txt       # Python dependencies
├── wrangler.toml         # Cloudflare configuration
├── public/               # Static files for Cloudflare Pages
│   └── index.html        # Main web interface
├── functions/            # Cloudflare Functions
│   └── api/
│       └── process.js    # API endpoint for CSV processing
├── templates/            # Flask templates (local development)
│   └── index.html        # Flask template
└── README.md            # This file
```

## API Endpoints

### POST /api/process

Processes uploaded CSV files and returns pricing calculations.

**Request**:
- Content-Type: `multipart/form-data`
- Body: Form data with `previous_file` and `current_file`

**Response**:
```json
{
  "success": true,
  "summary": {
    "total_items": 150,
    "avg_market_price": 12.50,
    "avg_store_price": 15.75,
    "total_value": 2362.50,
    "price_changes": {
      "increased": 45,
      "decreased": 30,
      "unchanged": 75
    }
  },
  "csv_data": "base64_encoded_csv_content",
  "filename": "updated_pricing_2023-10-30_14-30-25.csv"
}
```

## Pricing Algorithm

The application implements a sophisticated pricing algorithm:

1. **Base Price Calculation**: Uses the minimum of market price and low price
2. **Multiplier Adjustment**: 
   - Increases by 0.01 if inventory increased
   - Decreases by 0.05 if multiplier > 1.05
   - Decreases by 0.01 otherwise
3. **Quantity Bumps**:
   - 40+ items: +$0.05
   - 20-39 items: +$0.15
   - <20 items: +$0.25

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Performance

- **File Size Limit**: 16MB per file
- **Processing Time**: Typically <5 seconds for files up to 10,000 rows
- **Memory Usage**: Optimized for Cloudflare's serverless environment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the browser console for error messages
2. Verify your CSV files have the correct column headers
3. Ensure files are properly formatted (UTF-8 encoding recommended)
4. Open an issue on GitHub with detailed error information

## Changelog

### v1.0.0
- Initial release
- CSV file processing
- Pricing algorithm implementation
- Modern responsive UI
- Cloudflare Pages deployment 