# Gemini Image Captioner

A production-ready image captioning system using Google's Gemini 2.5 Flash API to generate detailed Vietnamese captions for batch image processing.

## 🚀 Quick Start

```bash
# Process images
python main.py

# Fix error files
python main.py --fix

# Show help
python main.py --help
```

## 📋 Features

- **Vietnamese Captions**: Detailed structured captions in Vietnamese
- **Batch Processing**: Handle thousands of images efficiently
- **API Key Rotation**: Automatic rotation for high throughput
- **Error Recovery**: Resume processing from checkpoints
- **Thread Safety**: Concurrent processing with graceful shutdown

## 🏗️ Architecture

```
src/                 # Source modules
tests/               # Test suite  
main.py             # CLI entry point
CLAUDE.md           # Comprehensive documentation
```

## 📖 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete project guide for developers
- **[README_REFACTORING.md](README_REFACTORING.md)** - Refactoring summary

## 🧪 Testing

```bash
python tests/run_tests.py        # All tests
python tests/integration_test.py # Integration tests
```

## ⚙️ Configuration

Edit `src/config.py`:
- Set your Gemini API keys
- Configure input/output directories
- Adjust processing parameters

## 📊 Status

- ✅ **Production Ready**: Comprehensive error handling and logging
- ✅ **Well Tested**: 60+ unit tests and integration tests  
- ✅ **Modular Design**: Clean architecture with single responsibility
- ✅ **Performance**: Concurrent processing with checkpoint recovery