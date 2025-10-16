#!/bin/bash

# Test runner script for onboarding service
echo "🧪 Running Onboarding Service Tests"
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run different test suites
echo ""
echo "🔍 Running unit tests..."
python -m pytest tests/test_onboarding.py -v

echo ""
echo "🔗 Running integration tests..."
python -m pytest tests/test_integration.py -v

echo ""
echo "⚡ Running performance tests..."
python -m pytest tests/test_performance.py -v

echo ""
echo "🚦 Running rate limiting tests..."
python -m pytest tests/test_rate_limiting.py -v

echo ""
echo "📊 Running all tests with coverage..."
python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

echo ""
echo "✅ Test execution completed!"
echo ""
echo "📁 Test artifacts:"
echo "   - HTML coverage report: htmlcov/index.html"
echo "   - Test results: Available in terminal output"
echo ""
echo "🔧 To run specific tests:"
echo "   pytest tests/test_onboarding.py::TestOnboardCluster::test_successful_onboarding -v"
echo "   pytest tests/ -k 'test_rate_limit' -v"
echo "   pytest tests/ --maxfail=1 -v"
