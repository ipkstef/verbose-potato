// Cloudflare Function for processing CSV files
export async function onRequestPost(context) {
  // Set larger timeout and memory limits for large files
  const env = context.env;
  const ctx = context;
  
  // Increase timeout for large file processing
  ctx.waitUntil = ctx.waitUntil || (() => {});
  try {
    const formData = await context.request.formData();
    const previousFile = formData.get('previous_file');
    const currentFile = formData.get('current_file');

    if (!previousFile || !currentFile) {
      return new Response(JSON.stringify({
        error: 'Both previous.csv and current.csv files are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Check file sizes
    const previousSize = previousFile.size;
    const currentSize = currentFile.size;
    const maxSize = 50 * 1024 * 1024; // 50MB limit
    
    if (previousSize > maxSize || currentSize > maxSize) {
      return new Response(JSON.stringify({
        error: `File too large. Maximum size is 50MB. Previous file: ${(previousSize / 1024 / 1024).toFixed(1)}MB, Current file: ${(currentSize / 1024 / 1024).toFixed(1)}MB`
      }), {
        status: 413,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Parse CSV files
    const previousText = await previousFile.text();
    const currentText = await currentFile.text();

    // Simple CSV parser (you might want to use a more robust library)
    const previous = parseCSV(previousText);
    const current = parseCSV(currentText);

    // Process the data
    const result = processPricingData(previous, current);

    if (result.error) {
      return new Response(JSON.stringify({
        error: result.error
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Create summary statistics
    const summary = createSummary(result.data);

    // Convert to CSV
    const csvContent = convertToCSV(result.data);

    // Encode for download
    const csvB64 = btoa(csvContent);

    return new Response(JSON.stringify({
      success: true,
      summary: summary,
      csv_data: csvB64,
      filename: `updated_pricing_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`
    }), {
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    return new Response(JSON.stringify({
      error: `Server error: ${error.message}`
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

function parseCSV(text) {
  const lines = text.split('\n');
  const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
  const data = [];

  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim()) {
      const values = lines[i].split(',').map(v => v.trim().replace(/"/g, ''));
      const row = {};
      headers.forEach((header, index) => {
        row[header] = values[index] || '';
      });
      data.push(row);
    }
  }

  return data;
}

function processPricingData(previous, current) {
  try {
    // Filter current data
    const filteredCurrent = current.filter(row => 
      row.Condition !== 'Unopened' && 
      row['TCG Market Price'] && 
      parseFloat(row['TCG Market Price']) > 0
    );

    // Create lookup for previous data
    const previousLookup = {};
    previous.forEach(row => {
      if (row['TCGplayer Id']) {
        previousLookup[row['TCGplayer Id']] = row;
      }
    });

    // Process each current row
    const processed = filteredCurrent.map(row => {
      const tcgId = row['TCGplayer Id'];
      const previousRow = previousLookup[tcgId] || {};
      
      // Calculate base price
      const marketPrice = parseFloat(row['TCG Market Price']) || 0;
      const lowPrice = parseFloat(row['TCG Low Price']) || 0;
      let basePrice = 50000.00;
      
      if (marketPrice > 0 && lowPrice > 0) {
        basePrice = Math.min(marketPrice, lowPrice);
      } else if (lowPrice > 0) {
        basePrice = lowPrice;
      } else if (marketPrice > 0) {
        basePrice = marketPrice;
      }

      // Calculate multiplier
      const oldQty = parseInt(previousRow['Old Qty'] || '0') || 0;
      const newQty = parseInt(row['Total Quantity'] || '0') || 0;
      const oldMultiplier = parseFloat(previousRow['Old Multiplier'] || '1.2') || 1.2;
      
      let multiplier = 1.2;
      if (oldQty === 0) {
        multiplier = 1.2;
      } else if (oldQty > 0 && newQty === 0) {
        multiplier = 1.2;
      } else if (oldQty < newQty) {
        multiplier = Math.round((oldMultiplier + 0.01) * 100) / 100;
      } else if (oldMultiplier - 0.05 > 1) {
        multiplier = Math.round((oldMultiplier - 0.05) * 100) / 100;
      } else {
        multiplier = Math.round((oldMultiplier - 0.01) * 100) / 100;
      }

      // Calculate store price
      const qty = parseInt(row['Total Quantity'] || '0') || 0;
      let rawPrice = marketPrice > 0 ? marketPrice : basePrice * multiplier;
      let bump = 0.25;
      
      if (qty >= 40) {
        bump = 0.05;
      } else if (qty >= 20) {
        bump = 0.15;
      }
      
      const storePrice = Math.round((rawPrice + Math.max(0, bump - rawPrice)) * 100) / 100;
      
      // Calculate diff
      const oldStorePrice = parseFloat(previousRow['Old My Store Price'] || '0') || 0;
      const diff = storePrice - oldStorePrice;

      return {
        ...row,
        'Old Multiplier': oldMultiplier,
        'Base Price': Math.round(basePrice * 100) / 100,
        'Multiplier': multiplier,
        'My Store Price': storePrice,
        'Old My Store Price': oldStorePrice,
        'Diff': Math.round(diff * 100) / 100
      };
    });

    return { data: processed, error: null };
  } catch (error) {
    return { data: null, error: error.message };
  }
}

function createSummary(data) {
  const totalItems = data.length;
  const marketPrices = data.map(row => parseFloat(row['TCG Market Price']) || 0).filter(p => p > 0);
  const storePrices = data.map(row => parseFloat(row['My Store Price']) || 0);
  const diffs = data.map(row => parseFloat(row['Diff']) || 0);

  const avgMarketPrice = marketPrices.length > 0 ? 
    Math.round(marketPrices.reduce((a, b) => a + b, 0) / marketPrices.length * 100) / 100 : 0;
  const avgStorePrice = Math.round(storePrices.reduce((a, b) => a + b, 0) / storePrices.length * 100) / 100;
  const totalValue = Math.round(storePrices.reduce((a, b) => a + b, 0) * 100) / 100;

  const priceChanges = {
    increased: diffs.filter(d => d > 0).length,
    decreased: diffs.filter(d => d < 0).length,
    unchanged: diffs.filter(d => d === 0).length
  };

  return {
    total_items: totalItems,
    avg_market_price: avgMarketPrice,
    avg_store_price: avgStorePrice,
    total_value: totalValue,
    price_changes: priceChanges
  };
}

function convertToCSV(data) {
  if (data.length === 0) return '';
  
  const headers = Object.keys(data[0]);
  const csvRows = [headers.join(',')];
  
  for (const row of data) {
    const values = headers.map(header => {
      const value = row[header] || '';
      return `"${value}"`;
    });
    csvRows.push(values.join(','));
  }
  
  return csvRows.join('\n');
} 