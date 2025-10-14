#!/bin/bash
# Run risk alert functionality test

echo "🚀 Starting Risk Alert Functionality Test..."
echo ""

chmod +x test_risk_alert_functionality.py

python3 test_risk_alert_functionality.py

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ All functionality tests passed!"
else
    echo "❌ Some tests failed (exit code: $exit_code)"
fi

exit $exit_code


