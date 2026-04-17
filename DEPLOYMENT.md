# VendorIQ — Deployment Guide

## Local Development (run immediately)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up environment variables
```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### 3. Set up Google OAuth credentials
1. Go to https://console.cloud.google.com
2. Create a project (or select existing)
3. Go to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Add Authorized Redirect URI: `http://localhost:8501`
7. Copy the **Client ID** and **Client Secret** into your `.env`

### 4. Enable Gmail API
1. In Google Cloud Console → **APIs & Services → Library**
2. Search for **Gmail API** → Enable it
3. Download `credentials.json` → place it in `config/credentials.json`

### 5. Initialize the database
```bash
python -m database.db_manager
```

### 6. Run the app
```bash
streamlit run app.py
```

Open http://localhost:8501 — sign in with any Google account.
`aryanranja771@gmail.com` gets Admin access automatically.

---

## Deploy to Streamlit Community Cloud (free, recommended)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
# Create a repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/smart-vendor.git
git push -u origin main
```

> ⚠ Make sure `.gitignore` is in place — never commit `.env`, `token.json`,
> `credentials.json`, or `vendor_history.db`

### Step 2 — Deploy on Streamlit Cloud
1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **New app**
4. Select your repo → branch: `main` → Main file: `app.py`
5. Click **Deploy**

### Step 3 — Add secrets on Streamlit Cloud
In your app settings → **Secrets**, add:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
GOOGLE_CLIENT_ID = "your_client_id"
GOOGLE_CLIENT_SECRET = "your_client_secret"
GOOGLE_REDIRECT_URI = "https://your-app-name.streamlit.app"
ADMIN_EMAIL = "aryanranja771@gmail.com"
```

### Step 4 — Update Google OAuth redirect URI
1. Go back to Google Cloud Console → Credentials → your OAuth client
2. Add **Authorized redirect URI**: `https://your-app-name.streamlit.app`
3. Save

### Step 5 — Add credentials.json as a secret (for Gmail API)
Since you can't upload files to Streamlit Cloud, encode credentials.json:

```bash
# On your local machine:
cat config/credentials.json | base64
```

Copy the output. In Streamlit secrets add:
```toml
GOOGLE_CREDENTIALS_B64 = "paste_base64_output_here"
```

Then update `gmail_auth.py` to decode it:
```python
import base64, json, os
b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if b64:
    data = json.loads(base64.b64decode(b64))
    with open("config/credentials.json", "w") as f:
        json.dump(data, f)
```

---

## Deploy to Railway (alternative, supports persistent storage)

Railway is better if you need the SQLite database to persist between deploys.

### Step 1 — Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### Step 2 — Deploy
```bash
railway init
railway up
```

### Step 3 — Set environment variables
```bash
railway variables set GEMINI_API_KEY=your_key
railway variables set GOOGLE_CLIENT_ID=your_id
railway variables set GOOGLE_CLIENT_SECRET=your_secret
railway variables set GOOGLE_REDIRECT_URI=https://your-app.railway.app
railway variables set ADMIN_EMAIL=aryanranja771@gmail.com
```

### Step 4 — Add a start command
Create `Procfile`:
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

---

## How Login Works

| Account | Access |
|---------|--------|
| Any Google account | User Dashboard (view offers, vendors, inventory snapshot) |
| `aryanranja771@gmail.com` | Full Admin Panel (add/update/delete inventory, manage DB, run pipeline) |

The admin email is set via the `ADMIN_EMAIL` environment variable — change it anytime without touching code.

---

## Folder Structure

```
smart-vendor/
├── app.py                    ← Streamlit entry point
├── main.py                   ← CLI email pipeline
├── requirements.txt
├── .env.example
├── auth/
│   └── google_oauth.py       ← Google OAuth2 login
├── frontend/
│   ├── styles.py             ← Shared CSS theme
│   ├── user_dashboard.py     ← User-facing dashboard
│   └── admin_dashboard.py    ← Admin inventory panel
├── ai/                       ← Gemini extraction
├── config/                   ← Settings + credentials
├── database/                 ← SQLite manager
├── gmail/                    ← Email reader + sender
├── inventory/                ← Inventory manager + updater
├── processing/               ← Ranking, normalization, profit
└── models/                   ← Offer dataclass
```
