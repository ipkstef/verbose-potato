#!/bin/bash

# TCG Pricing Calculator Deployment Script
# This script deploys the application to Cloudflare Pages

echo "🚀 Starting deployment to Cloudflare Pages..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI is not installed. Please install it first:"
    echo "npm install -g wrangler"
    exit 1
fi

# Check if user is logged in to Cloudflare
if ! wrangler whoami &> /dev/null; then
    echo "❌ Not logged in to Cloudflare. Please run:"
    echo "wrangler login"
    exit 1
fi

# Create public directory if it doesn't exist
if [ ! -d "public" ]; then
    echo "📁 Creating public directory..."
    mkdir -p public
fi

# Copy index.html to public directory if it doesn't exist
if [ ! -f "public/index.html" ]; then
    echo "📄 Copying index.html to public directory..."
    cp templates/index.html public/index.html
fi

# Deploy to Cloudflare Pages
echo "🌐 Deploying to Cloudflare Pages..."
wrangler pages deploy public --project-name tcg-pricing-calculator

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "🌍 Your app should be available at: https://tcg-pricing-calculator.pages.dev"
else
    echo "❌ Deployment failed. Please check the error messages above."
    exit 1
fi 