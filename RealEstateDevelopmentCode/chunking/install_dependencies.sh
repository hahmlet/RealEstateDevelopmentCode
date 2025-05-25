#!/bin/bash
# Municipal RAG System Dependencies Installation Script
# Run this script to install all required system and Python dependencies

echo "🚀 Installing Municipal RAG System Dependencies..."

# Update system packages
echo "📦 Updating system packages..."
apt-get update

# Install system dependencies
echo "🔧 Installing system dependencies..."
apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    default-jre \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --break-system-packages \
    unstructured[all-docs] \
    langchain \
    langchain-text-splitters \
    camelot-py[base] \
    tabula-py \
    pandas \
    faiss-cpu \
    sentence-transformers \
    JPype1 \
    pdfplumber

# Verify installations
echo "✅ Verifying installations..."
echo "Tesseract version:"
tesseract --version

echo "Poppler version:"
pdfinfo -v

echo "Java version:"
java -version

echo "🎉 Installation complete! All dependencies are ready."
echo "You can now run the RAG processing system."
