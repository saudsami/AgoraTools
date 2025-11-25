#!/bin/bash
# Quick Start Script for HTML to Markdown Conversion
# This script demonstrates how to use the converter

echo "================================================"
echo "Agora RTC HTML to Markdown Converter"
echo "================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found"

# Check if input directory is provided
if [ $# -eq 0 ]; then
    echo ""
    echo "Usage: $0 <input_directory> [output_directory]"
    echo ""
    echo "Example:"
    echo "  $0 docs_en docs_md"
    echo ""
    exit 1
fi

INPUT_DIR=$1
OUTPUT_DIR=${2:-"docs_md"}

# Validate input directory
if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Input directory '$INPUT_DIR' does not exist"
    exit 1
fi

echo "✓ Input directory found: $INPUT_DIR"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install -q beautifulsoup4 html2text lxml

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi

# Run conversion
echo ""
echo "Converting HTML to Markdown..."
echo "Input:  $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

python3 html_to_markdown_converter.py "$INPUT_DIR" "$OUTPUT_DIR" --create-index

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "✓ Conversion completed successfully!"
    echo "================================================"
    echo ""
    echo "Output location: $OUTPUT_DIR"
    echo ""
    echo "Next steps:"
    echo "  1. Check the generated files in $OUTPUT_DIR"
    echo "  2. Review README.md for navigation"
    echo "  3. Test internal links"
    echo ""
else
    echo ""
    echo "================================================"
    echo "✗ Conversion failed"
    echo "================================================"
    echo ""
    exit 1
fi
