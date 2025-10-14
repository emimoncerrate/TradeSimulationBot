#!/bin/bash
echo "🔍 Checking for running app instances..."
echo ""
ps aux | grep "python.*app.py" | grep -v grep
echo ""
COUNT=$(ps aux | grep "python.*app.py" | grep -v grep | wc -l)
echo "Total instances: $COUNT"

if [ $COUNT -gt 1 ]; then
    echo "⚠️  WARNING: Multiple instances detected!"
    echo "This can cause old code to still be running."
    echo ""
    echo "Run this to kill all:"
    echo "pkill -9 -f 'python.*app.py'"
fi

