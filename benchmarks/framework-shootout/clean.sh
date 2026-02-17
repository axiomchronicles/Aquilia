#!/usr/bin/env bash
# Cleanup script for framework-shootout

echo "Cleaning up..."
# Remove pycache
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete

# Remove .DS_Store
find . -name ".DS_Store" -delete

# Remove temporary test files
rm -f /tmp/bench*

# Remove logs
rm -f *.log

echo "Done."
