#!/bin/bash
# Complete app restart script

echo "🛑 Stopping all app instances..."
pkill -f "python.*app.py" 2>/dev/null
sleep 2

echo "🔍 Checking if any instances still running..."
RUNNING=$(ps aux | grep "python.*app.py" | grep -v grep)
if [ -z "$RUNNING" ]; then
    echo "✅ All instances stopped"
else
    echo "⚠️  Some instances still running, force killing..."
    ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
    sleep 1
    echo "✅ Force kill complete"
fi

echo ""
echo "🚀 Starting app..."
python3 app.py

