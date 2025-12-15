# Quick Setup Guide

## ✅ Completed
- PostgreSQL database with 6.7M rows imported
- Date range: Aug 2020 → Dec 2025
- Streamlit app configured for OpenRouter

## 🔧 Configuration Steps

### 1. Add your OpenRouter API Key

Edit [.env](.env) and replace the placeholder:

```bash
OPENROUTER_API_KEY=your-actual-key-here
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the App

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

### 4. Test with Sample Questions

Try these:
- "How much did I sell today?"
- "Top 10 products this month"
- "Sales by store last week"
- "Products losing money"

## 🌐 Deploy Online (Streamlit Cloud)

1. Push to GitHub
2. Go to https://share.streamlit.io
3. Connect your repo
4. Add OpenRouter API key in "Secrets":
   ```toml
   OPENROUTER_API_KEY = "your-key-here"
   ```

## 📊 Database Stats

- **Stores:** 9
- **Products:** 29,929
- **Sales Records:** 6,737,410
- **Date Range:** 2020-08-14 → 2025-12-14

## 🔍 LLM Providers

### Claude (via OpenRouter) - Default
- Model: `anthropic/claude-sonnet-4-5:beta`
- Best accuracy for complex queries
- Requires OpenRouter API key

### Ollama - Optional
- For local/private deployment
- Setup later on server (192.168.0.160)
- Uses RTX 3060 GPU
