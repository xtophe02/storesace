# StoreSace - Deployment Guide

Three deployment options for different scenarios.

---

## 🚀 Option 1: Streamlit Cloud (Fastest - Tonight's Demo)

**Best for:** Quick demo, sharing with Ivo immediately

### Steps

1. **Push to GitHub**
```bash
cd /home/chris/projects/storesace
git init
git add .
git commit -m "StoreSace initial commit"
git remote add origin https://github.com/xtophe02/storesace.git
git push -u origin main
```

2. **Deploy on Streamlit Cloud**
- Visit: https://share.streamlit.io
- Login with GitHub
- Click "New app"
- Select: `xtophe02/storesace` → `app.py`
- Advanced settings → Secrets:
```toml
[secrets]
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
DB_HOST = "your-database-host"  # See note below
DB_PASSWORD = "storesace_dev"
```

3. **Database Access**

⚠️ **Problem:** Streamlit Cloud can't access `localhost`

**Solutions:**

**A) Expose PostgreSQL via Cloudflare Tunnel** (Recommended)
```bash
# On your laptop
cloudflared tunnel --url tcp://localhost:5432

# Output: https://random-id.trycloudflare.com
# Use this as DB_HOST in Streamlit secrets
```

**B) Use cloud PostgreSQL** (ElephantSQL free tier)
- Visit: https://www.elephantsql.com
- Create free "Tiny Turtle" instance
- Import data
- Use their hostname in secrets

**C) Open PostgreSQL to internet** (Not recommended)
```bash
# Edit docker-compose.yml
ports:
  - "0.0.0.0:5432:5432"  # WARNING: Exposes to internet!

# Set strong password, restrict IPs
```

**Result:** `https://storesace.streamlit.app`

**Pros:**
- ✅ Free
- ✅ Public URL in 5 minutes
- ✅ Auto-updates from GitHub
- ✅ HTTPS included

**Cons:**
- ❌ Database connectivity complex
- ❌ Can't use Ollama (no GPU)

---

## 🏠 Option 2: Your Server (192.168.0.160) - Full Control

**Best for:** Local LLM (Ollama), data privacy, GPU usage

### Prerequisites

On your server (192.168.0.160):
```bash
# Install Docker (if not already)
curl -fsSL https://get.docker.com | sh

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull LLM model
ollama pull llama3.1:8b
# or for better SQL: ollama pull codellama:13b
```

### Deployment

1. **Copy project to server**
```bash
# From your laptop
scp -r /home/chris/projects/storesace chris@192.168.0.160:~/apps/

# SSH into server
ssh chris@192.168.0.160
cd ~/apps/storesace
```

2. **Configure environment**
```bash
cp .env.example .env

# Edit .env
nano .env

# Set:
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
DB_HOST=localhost
```

3. **Start services**
```bash
# PostgreSQL
docker compose up -d

# Import data (if not done)
./import_complete.py

# Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start Streamlit
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

4. **Access**
- From LAN: `http://192.168.0.160:8501`
- From internet: Use Cloudflare Tunnel (see below)

### Expose to Internet (Cloudflare Tunnel - Free)

```bash
# On server
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Create tunnel
cloudflared tunnel --url http://localhost:8501

# Output: https://random-id.trycloudflare.com
# Share this with Ivo!
```

**Permanent tunnel:**
```bash
cloudflared tunnel login
cloudflared tunnel create storesace
cloudflared tunnel route dns storesace storesace.yourdomain.com
cloudflared tunnel run storesace
```

**Pros:**
- ✅ Free
- ✅ Full control
- ✅ Can use Ollama (local LLM)
- ✅ Data stays local
- ✅ Uses RTX 3060 GPU

**Cons:**
- ❌ Server must stay on
- ❌ More setup complexity

---

## 🌐 Option 3: Production VPS (Professional)

**Best for:** Real production deployment

### Setup

1. **Rent VPS** (~€5/month)
- Hetzner CX11 (€4.15/month)
- DigitalOcean Basic Droplet ($6/month)
- Linode Nanode ($5/month)

2. **Install on VPS**
```bash
# SSH into VPS
ssh root@your-vps-ip

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone repo
git clone https://github.com/xtophe02/storesace.git
cd storesace

# Setup
cp .env.example .env
# Edit .env with production values

# Start
docker compose -f docker-compose.prod.yml up -d
```

3. **Setup domain + SSL**
```bash
# Buy domain: storesace.com (~€10/year)
# Point A record to VPS IP

# Install Nginx + Certbot
apt install nginx certbot python3-certbot-nginx

# Configure Nginx
cat > /etc/nginx/sites-available/storesace << 'EOF'
server {
    listen 80;
    server_name storesace.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
EOF

ln -s /etc/nginx/sites-available/storesace /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Get SSL certificate
certbot --nginx -d storesace.com
```

**Result:** `https://storesace.com` (professional URL)

**Pros:**
- ✅ Professional domain
- ✅ HTTPS included
- ✅ High uptime
- ✅ Can scale

**Cons:**
- ❌ Monthly cost (~€5)
- ❌ No GPU (unless expensive instance)

---

## 🔐 Security Best Practices

### For Any Deployment

1. **Environment Variables**
Never commit secrets to git:
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
```

2. **Database Security**
```bash
# Change default password
DB_PASSWORD=generate-strong-password-here

# Restrict PostgreSQL access
# In docker-compose.yml:
ports:
  - "127.0.0.1:5432:5432"  # Only localhost
```

3. **API Keys**
```bash
# Store in secrets manager or .env (never in code)
ANTHROPIC_API_KEY=sk-ant-your-actual-key
```

4. **Read-Only Queries**
The app only runs SELECT queries, but add PostgreSQL user with read-only:
```sql
CREATE USER storesace_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE storesace TO storesace_readonly;
GRANT USAGE ON SCHEMA prod_515383678 TO storesace_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA prod_515383678 TO storesace_readonly;
```

---

## 📊 Monitoring & Maintenance

### Check Logs

**Streamlit Cloud:**
- View in dashboard: https://share.streamlit.io

**Server:**
```bash
# Application logs
tail -f streamlit.log

# PostgreSQL logs
docker logs storesace_db

# Ollama logs
journalctl -u ollama -f
```

### Backups

```bash
# Automated backup script
cat > ~/backup-storesace.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec storesace_db pg_dump -U storesace storesace -F c > backup_${DATE}.dump
# Optional: Upload to cloud
# rclone copy backup_${DATE}.dump remote:backups/
EOF

chmod +x ~/backup-storesace.sh

# Cron job (daily at 3 AM)
crontab -e
# Add: 0 3 * * * ~/backup-storesace.sh
```

---

## 🎯 Recommendation for You

**Tonight (Demo for Ivo):**
- Option 2 (Your Server) + Cloudflare Tunnel
- Use Ollama (show local LLM capability)
- Result: `https://random-id.trycloudflare.com`

**This Week (If Ivo likes it):**
- Option 3 (VPS) or keep Option 2
- Add authentication
- Switch to permanent domain

**Why:** Shows both cloud (Claude) and local (Ollama) capabilities, free, quick.

---

## 🚦 Quick Start Commands

### Local Development
```bash
# 1. Start PostgreSQL
docker compose up -d

# 2. Import data
./import_complete.py

# 3. Setup Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env

# 5. Run
streamlit run app.py
```

### Server Deployment
```bash
# SSH to server
ssh chris@192.168.0.160

# Pull latest
cd ~/apps/storesace
git pull

# Restart
docker compose restart
pkill -f streamlit
streamlit run app.py --server.port 8501 &

# Expose
cloudflared tunnel --url http://localhost:8501
```

---

## 📞 Troubleshooting

### "Can't connect to database"
```bash
# Check if PostgreSQL is running
docker ps | grep storesace_db

# Check connection
docker exec -it storesace_db psql -U storesace -d storesace -c "SELECT 1;"
```

### "Ollama not found"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Pull model
ollama pull llama3.1:8b
```

### "Claude API error"
```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Test API
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-5-20250929","max_tokens":1024,"messages":[{"role":"user","content":"test"}]}'
```

---

## 📝 Next Steps After Deployment

1. **Test with Ivo's questions**
2. **Gather feedback**
3. **Add authentication** (if needed)
4. **Improve prompts** based on errors
5. **Add more example queries**
6. **Consider Next.js upgrade** (if UI needs work)
