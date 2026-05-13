# SocketForm

Prosthetic socket design pipeline — free, public, open source.

**Live site**: `https://YOUR_USERNAME.github.io/socketform`  
**API**: `https://socketform-backend.up.railway.app`

---

## Repo structure

```
socketform/
├── index.html              ← frontend (served by GitHub Pages)
├── .github/
│   └── workflows/
│       └── deploy.yml      ← auto-deploys frontend on push to main
└── backend/
    ├── server.py           ← FastAPI + Open3D processing API
    ├── requirements.txt
    └── Dockerfile          ← used by Railway
```

---

## Deploy in 4 steps

### Step 1 — Create the GitHub repo

1. Go to [github.com/new](https://github.com/new)
2. Name it `socketform`, set it to **Public**
3. Don't initialise with a README (you'll push this code)

Then push this code:

```bash
cd socketform                        # this folder
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/socketform.git
git push -u origin main
```

### Step 2 — Enable GitHub Pages

1. In your repo, go to **Settings → Pages**
2. Under "Source", select **GitHub Actions**
3. The deploy workflow (`.github/workflows/deploy.yml`) runs automatically
4. Your site will be live at `https://YOUR_USERNAME.github.io/socketform` in ~1 minute

### Step 3 — Deploy the backend to Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Select your `socketform` repo
4. Railway will detect the `backend/Dockerfile` — click **Deploy**
5. Once deployed, click the service → **Settings → Networking → Generate Domain**
6. Copy the URL (e.g. `https://socketform-backend.up.railway.app`)

Railway's free tier gives 500 CPU-hours/month — more than enough for a clinical preview tool.

### Step 4 — Connect frontend to backend

Open `index.html` and set line 2 of the script section:

```js
const API_URL = 'https://socketform-backend.up.railway.app';
```

Then commit and push:

```bash
git add index.html
git commit -m "connect to Railway backend"
git push
```

GitHub Actions redeploys automatically. Done — your site is live and fully wired.

---

## Local development

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Terminal 2 — frontend
# Just open index.html in your browser, or:
python -m http.server 3000
# visit http://localhost:3000
# Set API_URL = 'http://localhost:8000' in index.html for local testing
```

---

## Updating the site

Any push to `main` automatically:
- Redeploys the frontend via GitHub Actions (GitHub Pages)
- Triggers a redeploy on Railway (backend)

No manual steps needed after initial setup.

---

## Cost

| Service | Cost |
|---------|------|
| GitHub Pages | Free forever |
| Railway free tier | Free (500 CPU-hr/mo) |
| Custom domain | Optional — point any domain at GitHub Pages for free |

---

## What's next (step 4)

- Manufacturer catalog API — match socket to foot/pylon components by residual limb level
- Patient record storage (HIPAA-compliant — use Railway + PostgreSQL or Supabase)
- Prosthetist accounts and case management
