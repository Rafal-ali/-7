# Deploy Smart Parking on Koyeb (Free)

## 1) Push latest code to GitHub
```bash
git add .
git commit -m "Prepare production deployment"
git push origin main
```

## 2) Create app on Koyeb
1. Sign in to Koyeb with GitHub.
2. Click **Create App**.
3. Choose **GitHub** and select your repository.
4. Branch: `main`.
5. Build method: **Dockerfile**.
6. Web service port: leave default (Koyeb provides `PORT`).
7. Instance type: Free.

## 3) Environment variables
Add:
- `SECRET_KEY` = any strong random string
- `DB_PATH` = `/data/parking.db`

## 4) Persistent volume (important)
Add a volume:
- Mount path: `/data`
- Size: smallest available

## 5) Deploy
Click **Deploy**.
After success, Koyeb gives a public URL (HTTPS).

## 6) Verify
Open:
- `/login`
- login as admin: `admin / admin123`

## Notes
- If volume is not attached, SQLite data may reset on restart.
- On free tier, app may sleep when idle.
