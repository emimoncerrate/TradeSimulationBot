#!/bin/bash
# Script to merge devbranch into B-branch

echo "🔍 Checking current branch..."
git branch --show-current

echo ""
echo "📥 Fetching latest from origin/devbranch..."
git fetch origin devbranch

echo ""
echo "🔀 Merging origin/devbranch into B-branch..."
git merge origin/devbranch --no-edit

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Merge completed successfully!"
    echo ""
    echo "📊 Summary of changes:"
    git log --oneline -5
else
    echo ""
    echo "⚠️  Merge conflicts detected!"
    echo "Run 'git status' to see conflicted files"
fi

