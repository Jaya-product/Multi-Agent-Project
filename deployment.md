# 🚀 Deployment Guide: Dubai AI Travel Planning System

This document outlines production deployment strategies for the **Dubai AI Travel Planning System**—an autonomous multi-agent platform orchestrated via **LangGraph** with a **Streamlit** visual studio.

---

## 📋 Table of Contents

1. [Architecture & Runtime Profile](#1-architecture--runtime-profile)
2. [Environment Variables Reference](#2-environment-variables-reference)
3. [Deployment Option 1: Streamlit Community Cloud (Quickest & Free)](#3-deployment-option-1-streamlit-community-cloud)
4. [Deployment Option 2: Docker & Docker Compose (Recommended for Self-Hosting)](#4-deployment-option-2-docker--docker-compose)
5. [Deployment Option 3: Production Linux VM with Systemd, Nginx & SSL](#5-deployment-option-3-production-linux-vm-systemd--nginx)
6. [Deployment Option 4: Serverless Containers (Google Cloud Run)](#6-deployment-option-4-serverless-containers-google-cloud-run)
7. [Deployment Option 5: PaaS Platforms (Render / Railway / Hugging Face Spaces)](#7-deployment-option-5-paas-platforms)
8. [Resource Sizing & Production Tuning](#8-resource-sizing--production-tuning)
9. [Troubleshooting & Common Pitfalls](#9-troubleshooting--common-pitfalls)

---

## 1. Architecture & Runtime Profile

- **Application Type:** Stateful Multi-Agent Studio (LangGraph StateGraph + Streamlit)
- **Primary Process:** `streamlit run app/main.py`
- **Default Port:** `8501` (HTTP + WebSockets)
- **Local Data Storage:** Embedded SQLite database (`data/database/dubai_travel.db`)
- **External Network Dependencies:**
  - LLM Provider API (Google Gemini or Groq)
  - Open-Meteo Weather API (`api.open-meteo.com` — 100% Free, Unmetered)
  - OSRM Road Routing API (`router.project-osrm.org` — 100% Free Open Routing)

---

## 2. Environment Variables Reference

Create a `.env` file in the project root based on `.env.example`:

| Variable | Required | Default | Description / Valid Values |
| :--- | :---: | :---: | :--- |
| `LLM_PROVIDER` | **Yes** | `google` | Active LLM client: `google`, `groq`, `openai`, `ollama` |
| `LLM_MODEL_NAME` | **Yes** | `gemini-2.5-flash` | Model identifier (e.g., `gemini-2.5-flash`, `llama-3.3-70b-versatile`) |
| `GOOGLE_API_KEY` | Conditional | — | Required when `LLM_PROVIDER=google` ([Get Key](https://aistudio.google.com/)) |
| `GROQ_API_KEY` | Conditional | — | Required when `LLM_PROVIDER=groq` ([Get Key](https://console.groq.com/keys)) |
| `OPENAI_API_KEY` | Conditional | — | Required when `LLM_PROVIDER=openai` |
| `LLM_TEMPERATURE` | No | `0.3` | Model sampling temperature (0.0 – 1.0) |
| `LLM_MAX_TOKENS` | No | `4096` | Maximum completion token budget per agent call |
| `SQLITE_DB_PATH` | No | `data/database/dubai_travel.db` | Absolute or relative path to SQLite database |
| `ENABLE_WEATHER_INTEGRATION` | No | `true` | Weather-aware pacing via Open-Meteo API |
| `ENABLE_OSRM_ROUTING` | No | `true` | Real road routing via OSRM (falls back to Haversine) |
| `ENABLE_HUMAN_IN_THE_LOOP` | No | `false` | Pause graph for user inspection prior to QA node |
| `MAX_REVIEW_ITERATIONS` | No | `3` | Max self-correction retry cycles before forced synthesis |

---

## 3. Deployment Option 1: Streamlit Community Cloud

The easiest zero-cost deployment method for public or private GitHub repositories.

### Steps:
1. Push your repository to **GitHub** (ensure `.env` is omitted; `.gitignore` handles this).
2. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
3. Click **"New App"** and configure:
   - **Repository:** `your-username/dubai-ai-travel-planner`
   - **Branch:** `main`
   - **Main file path:** `app/main.py`
4. Click **"Advanced Settings"** ➔ **"Secrets"** and enter your environment secrets:
   ```toml
   LLM_PROVIDER = "google"
   LLM_MODEL_NAME = "gemini-2.5-flash"
   GOOGLE_API_KEY = "AIzaSy..."
   SQLITE_DB_PATH = "data/database/dubai_travel.db"
   ```
5. Click **"Deploy!"**. The seed SQLite database will build automatically during startup.

---

## 4. Deployment Option 2: Docker & Docker Compose

Recommended for self-hosted instances, cloud VPS (AWS EC2, DigitalOcean, Hetzner), or private servers.

### 4.1 Quick Start with Docker Compose
The repository includes a ready-to-use [`Dockerfile`](file:///c:/Users/jaya.manocha/Documents/myProjects/Multi%20Agent/Dockerfile) and [`docker-compose.yml`](file:///c:/Users/jaya.manocha/Documents/myProjects/Multi%20Agent/docker-compose.yml).

1. Ensure your `.env` file exists:
   ```bash
   cp .env.example .env
   # Add your GOOGLE_API_KEY or GROQ_API_KEY to .env
   ```

2. Build and launch the container in detached mode:
   ```bash
   docker compose up -d --build
   ```

3. Check container status:
   ```bash
   docker compose ps
   docker compose logs -f
   ```

4. Access the application in your browser at `http://localhost:8501`.

### 4.2 Standalone Docker Commands

Build image:
```bash
docker build -t dubai-ai-travel-planner:latest .
```

Run container:
```bash
docker run -d \
  --name dubai-travel \
  -p 8501:8501 \
  -e LLM_PROVIDER=google \
  -e GOOGLE_API_KEY="your-api-key" \
  -v dubai_data:/app/data/database \
  --restart unless-stopped \
  dubai-ai-travel-planner:latest
```

---

## 5. Deployment Option 3: Production Linux VM (Systemd + Nginx + SSL)

For dedicated Ubuntu/Debian instances on AWS EC2, DigitalOcean Droplets, or GCP Compute Engine.

### 5.1 System Setup & Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip git nginx certbot python3-certbot-nginx curl sqlite3
```

### 5.2 Clone Repository & Virtual Environment
```bash
cd /opt
sudo git clone https://github.com/your-org/dubai-ai-travel-planner.git
sudo chown -R $USER:$USER /opt/dubai-ai-travel-planner
cd /opt/dubai-ai-travel-planner

python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Rebuild seed database
python data/build_seed_db.py

# Configure production .env
cp .env.example .env
nano .env
```

### 5.3 Configure Systemd Service
Create the service unit file:
```bash
sudo nano /etc/systemd/system/dubai-travel.service
```

Paste the following configuration:
```ini
[Unit]
Description=Dubai AI Travel Planning Studio (Streamlit + LangGraph)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/dubai-ai-travel-planner
Environment="PATH=/opt/dubai-ai-travel-planner/venv/bin"
EnvironmentFile=/opt/dubai-ai-travel-planner/.env
ExecStart=/opt/dubai-ai-travel-planner/venv/bin/streamlit run app/main.py \
    --server.port=8501 \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo chown -R www-data:www-data /opt/dubai-ai-travel-planner
sudo systemctl daemon-reload
sudo systemctl enable dubai-travel
sudo systemctl start dubai-travel
sudo systemctl status dubai-travel
```

### 5.4 Configure Nginx Reverse Proxy with WebSocket Support
Streamlit requires persistent WebSocket connections. Create the Nginx site configuration:
```bash
sudo nano /etc/nginx/sites-available/dubai-travel
```

Paste:
```nginx
server {
    listen 80;
    server_name travel.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        
        # WebSocket Upgrade Headers (Essential for Streamlit)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Extended timeouts for long-running multi-agent streaming
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

Enable the site and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/dubai-travel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5.5 Obtain Free SSL Certificate via Let's Encrypt
```bash
sudo certbot --nginx -d travel.yourdomain.com
```

---

## 6. Deployment Option 4: Serverless Containers (Google Cloud Run)

Google Cloud Run provides serverless container execution with automatic scaling.

### 6.1 Build & Submit Container to Artifact Registry
```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="me-central1" # (Dubai / Middle East Region)

gcloud config set project $PROJECT_ID

gcloud builds submit --tag gcr.io/$PROJECT_ID/dubai-travel-planner:latest .
```

### 6.2 Deploy to Cloud Run
> **Important:** Enable `--session-affinity` and set port `8501` to ensure Streamlit's WebSocket connection remains tied to the active container.

```bash
gcloud run deploy dubai-travel-planner \
  --image gcr.io/$PROJECT_ID/dubai-travel-planner:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8501 \
  --memory 2Gi \
  --cpu 2 \
  --session-affinity \
  --set-env-vars LLM_PROVIDER=google,LLM_MODEL_NAME=gemini-2.5-flash \
  --set-secrets GOOGLE_API_KEY=GOOGLE_API_KEY:latest
```

---

## 7. Deployment Option 5: PaaS Platforms

### 7.1 Render (Web Service)
1. Link your GitHub repo to [Render](https://render.com/).
2. Select **"Web Service"** with environment **Docker**.
3. Set **Start Command:** Leave empty (uses `Dockerfile` `ENTRYPOINT`).
4. Set Environment Variables:
   - `GOOGLE_API_KEY` = `your_key`
   - `LLM_PROVIDER` = `google`
5. Render detects port `8501` automatically.

### 7.2 Railway
1. Click **"New Project"** ➔ **"Deploy from GitHub repo"**.
2. Under **Variables**, add `GOOGLE_API_KEY`, `LLM_PROVIDER=google`.
3. Under **Settings**, set **Port** to `8501`.

### 7.3 Hugging Face Spaces
Create a new Space with the **Streamlit SDK** or **Docker SDK**.
Add your secret in Space Settings ➔ **Variables and secrets**.

---

## 8. Resource Sizing & Production Tuning

| Metric | Minimum Sizing | Recommended Production Sizing |
| :--- | :--- | :--- |
| **vCPU** | 1 Core | 2 Cores |
| **RAM** | 1.0 GB | 2.0 – 4.0 GB |
| **Disk Space** | 2 GB | 10 GB (for SQLite DB and logging) |
| **Max Concurrent Graph Runs** | 2 – 3 parallel users | 10 – 15 parallel users |

### Streamlit Production Config (`.streamlit/config.toml`)
The repository includes optimized production settings in [`.streamlit/config.toml`](file:///c:/Users/jaya.manocha/Documents/myProjects/Multi%20Agent/.streamlit/config.toml):
```toml
[theme]
base = "light"
primaryColor = "#d97706"
backgroundColor = "#f8fafc"
secondaryBackgroundColor = "#ffffff"
textColor = "#0f172a"
font = "sans serif"

[client]
showErrorDetails = false

[browser]
gatherUsageStats = false

[server]
headless = true
enableCORS = false
enableXsrfProtection = true
```

---

## 9. Troubleshooting & Common Pitfalls

### Issue 1: Infinite "Please wait..." or WebSocket Disconnections
- **Cause:** Reverse proxy (Nginx / Cloudflare) is buffering or dropping WebSocket connections.
- **Fix:** Ensure `proxy_set_header Upgrade $http_upgrade;` and `proxy_set_header Connection "upgrade";` are enabled in your Nginx config. In Cloudflare, verify WebSockets are enabled under the Network tab.

### Issue 2: SQLite `sqlite3.OperationalError: unable to open database file`
- **Cause:** Permission mismatch when running under Docker or systemd user (`www-data`).
- **Fix:** Grant write permissions to the SQLite directory:
  ```bash
  sudo chown -R www-data:www-data /opt/dubai-ai-travel-planner/data/database
  sudo chmod -R 775 /opt/dubai-ai-travel-planner/data/database
  ```

### Issue 3: LLM Provider Quota / Rate Limiting
- **Cause:** Reached free tier limits for Gemini or Groq during multiple rapid test loops.
- **Fix:**
  - Switch provider in the UI sidebar dropdown (e.g., from `google` to `groq`).
  - Or configure fallback settings in `.env`:
    ```ini
    FALLBACK_LLM_PROVIDER=groq
    FALLBACK_LLM_MODEL=llama-3.3-70b-versatile
    FALLBACK_LLM_API_KEY=your_groq_key
    ```

### Issue 4: Healthcheck Endpoint Verification
Verify the running instance anytime using the native Streamlit health check endpoint:
```bash
curl -I http://localhost:8501/_stcore/health
# Expected Output: HTTP/1.1 200 OK
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` or API keys:** Keep `.env` in `.gitignore` at all times.
2. **Run containers as non-root:** The provided `Dockerfile` creates and switches to unprivileged `appuser`.
3. **Use HTTPS in production:** Always terminate SSL at Nginx, Cloudflare, or Cloud Load Balancer.
4. **Regular Dependency Audits:** Periodically run `pip audit` to monitor upstream Python security advisories.
