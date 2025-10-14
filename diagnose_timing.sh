#!/bin/bash
echo "🔍 Diagnosing /risk-alert timing issue..."
echo ""

echo "1. Checking for multiple app instances..."
INSTANCES=$(ps aux | grep "python.*app.py" | grep -v grep | wc -l)
echo "   Found $INSTANCES running instance(s)"
if [ $INSTANCES -gt 1 ]; then
    echo "   ⚠️  WARNING: Multiple instances detected!"
    echo "   This causes old slow code to still be running."
    ps aux | grep "python.*app.py" | grep -v grep
fi
echo ""

echo "2. Checking recent logs for timing..."
if [ -f "jain_global_slack_trading_bot.log" ]; then
    echo "   Last /risk-alert attempt:"
    tail -100 jain_global_slack_trading_bot.log | grep -A 5 "risk-alert" | tail -20
else
    echo "   ⚠️  Log file not found"
fi
echo ""

echo "3. Recommendations:"
if [ $INSTANCES -gt 1 ]; then
    echo "   ❗ Kill ALL instances: pkill -9 -f 'python.*app.py'"
    echo "   ❗ Then restart: python3 app.py"
elif [ $INSTANCES -eq 0 ]; then
    echo "   ❗ No app running - start it: python3 app.py"
else
    echo "   ✅ Single instance running"
    echo "   💡 Check if you restarted after the code fix"
fi



