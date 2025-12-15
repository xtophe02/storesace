# Deployment Guide

## Option 1: Streamlit Cloud (Recommended for Demo)

**Free, no account needed for Cloudflare Tunnel, easy sharing**

### Steps:

1. **Push to GitHub** (if not already)
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"
   - Select your repo: `storesace`
   - Main file: `app.py`
   - Click "Advanced settings"
   - Add secrets:
     ```toml
     OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
     DB_HOST = "your-db-host"
     DB_PORT = "5432"
     DB_NAME = "storesace"
     DB_USER = "storesace"
     DB_PASSWORD = "storesace_dev"
     DB_SCHEMA = "prod_515383678"
     ```

**Note:** Database needs to be publicly accessible or use Streamlit's built-in connection.

---

## Option 2: Docker Compose (Local/Server)

**For running on your laptop or server (192.168.0.160)**

### Quick Start:

```bash
# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f streamlit

# Access at http://localhost:8501
```

### Stop:
```bash
docker-compose down
```

---

## Option 3: Cloudflare Tunnel (Make Local Accessible)

**Share your local Docker instance online - NO ACCOUNT NEEDED**

### Steps:

1. **Install Cloudflare Tunnel**:
   ```bash
   # Linux/WSL
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared-linux-amd64.deb
   ```

2. **Start your app with Docker**:
   ```bash
   docker-compose up -d
   ```

3. **Create tunnel (no login required)**:
   ```bash
   cloudflared tunnel --url http://localhost:8501
   ```

4. **Share the URL** - Cloudflare will give you a public URL like:
   ```
   https://random-name.trycloudflare.com
   ```

**Note:** This is temporary and free. URL changes each time you restart the tunnel.

---

## Recommended Approach for Tonight's Demo

**Use Docker Compose + Cloudflare Tunnel**:

1. Start services: `docker-compose up -d`
2. Verify working: `http://localhost:8501`
3. Share online: `cloudflared tunnel --url http://localhost:8501`
4. Send Ivo the `trycloudflare.com` URL

**Why:**
- Database already imported (6.7M rows)
- Works on your laptop (RTX 5080)
- No external DB setup needed
- Free and instant
- Can test locally first

---

## Database Notes

### If using Streamlit Cloud:
You need to either:
1. Make your PostgreSQL publicly accessible (not recommended)
2. Use a cloud database (Supabase, Railway, etc.)
3. Export to SQLite for demo purposes

### If using Docker Compose:
Database is already set up and populated with 6.7M rows.
