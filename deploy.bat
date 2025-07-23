@echo off
REM TCG Pricing Calculator Deployment Script for Windows
REM This script deploys the application to Cloudflare Pages

echo 🚀 Starting deployment to Cloudflare Pages...

REM Check if wrangler is installed
wrangler --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Wrangler CLI is not installed. Please install it first:
    echo npm install -g wrangler
    pause
    exit /b 1
)

REM Check if user is logged in to Cloudflare
wrangler whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Not logged in to Cloudflare. Please run:
    echo wrangler login
    pause
    exit /b 1
)

REM Create public directory if it doesn't exist
if not exist "public" (
    echo 📁 Creating public directory...
    mkdir public
)

REM Copy index.html to public directory if it doesn't exist
if not exist "public\index.html" (
    echo 📄 Copying index.html to public directory...
    copy templates\index.html public\index.html
)

REM Deploy to Cloudflare Pages
echo 🌐 Deploying to Cloudflare Pages...
wrangler pages deploy public --project-name tcg-pricing-calculator

if %errorlevel% equ 0 (
    echo ✅ Deployment successful!
    echo 🌍 Your app should be available at: https://tcg-pricing-calculator.pages.dev
) else (
    echo ❌ Deployment failed. Please check the error messages above.
    pause
    exit /b 1
)

pause 