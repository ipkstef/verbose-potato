// Cloudflare Function for summary calculations only
export async function onRequestPost(context) {
  try {
    const data = await context.request.json();
    
    if (!data.processed_data || !Array.isArray(data.processed_data)) {
      return new Response(JSON.stringify({
        error: 'Processed data is required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Create summary statistics
    const summary = createSummary(data.processed_data);

    return new Response(JSON.stringify({
      success: true,
      summary: summary
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