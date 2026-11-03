# Production Deployment Guide — Finance Tracker Pro

This guide covers 3 production deployment strategies for **Finance Tracker Pro**:
1. **Option A: Linux VPS / Cloud VM with Docker Compose (Recommended for full control & MySQL)**
2. **Option B: Modern Cloud PaaS (Railway / Render)**
3. **Option C: AWS / GCP / DigitalOcean (Managed Containers)**

---

## 🔒 Pre-Deployment Security Checklist

Before deploying to any public server:
1. **Change SECRET_KEY**: Generate a strong 50+ character random string:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```
2. **Disable DEBUG**: Set `DEBUG=False` in your production environment.
3. **Set ALLOWED_HOSTS**: Set to your domain (e.g. `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`).
4. **Strong DB Passwords**: Set unique passwords for `MYSQL_ROOT_PASSWORD` and `DB_PASSWORD`.
5. **HTTPS / SSL**: Ensure all traffic is encrypted with Let's Encrypt or Cloudflare.

---

## 🚀 Option A: Linux VPS with Docker Compose (Recommended)

Works on any Ubuntu 22.04 / 24.04 server (DigitalOcean Droplet, AWS EC2, Hetzner, Linode, Vultr):

### Step 1: Connect to your server & install Docker
```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose plugin
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### Step 2: Clone your repository
```bash
git clone https://github.com/<your-username>/finance-tracker-pro.git
cd finance-tracker-pro
```

### Step 3: Configure `.env`
```bash
cp .env.example .env
nano .env
```
Fill in production values:
```ini
SECRET_KEY=generate_a_random_50_char_string_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

DB_NAME=finance_tracker
DB_USER=finance_user
DB_PASSWORD=YourStrongDatabasePassword123!
MYSQL_ROOT_PASSWORD=YourStrongRootPassword123!
DB_HOST=db
DB_PORT=3306

ML_SERVICE_URL=http://ml_service:5001
```

### Step 4: Build and Launch with Production Compose
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### Step 5: Seed Demo Data or Create Admin User
```bash
# Seed initial demo data
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_demo_data

# Create your own superuser
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### Step 6: Enable Free SSL with Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## ☁️ Option B: Railway (One-Click Cloud PaaS)

Railway is the simplest cloud hosting platform with automatic GitHub CI/CD:

1. Push your code to a GitHub repository:
   ```bash
   git push -u origin main
   ```
2. Go to [railway.app](https://railway.app) and sign in with GitHub.
3. Click **"New Project"** ➔ **"Deploy from GitHub repo"**.
4. Add **MySQL Database**: Click **"New"** ➔ **"Database"** ➔ **"Add MySQL"**.
5. Set environment variables on the backend service in Railway:
   - `DEBUG`: `False`
   - `SECRET_KEY`: `<your_secret_key>`
   - `DB_HOST`: `${{MySQL.MYSQLHOST}}`
   - `DB_NAME`: `${{MySQL.MYSQLDATABASE}}`
   - `DB_USER`: `${{MySQL.MYSQLUSER}}`
   - `DB_PASSWORD`: `${{MySQL.MYSQLPASSWORD}}`
   - `DB_PORT`: `${{MySQL.MYSQLPORT}}`
   - `ML_SERVICE_URL`: `<url_of_flask_service>`
6. Deploy the `ml_service` as a second service linked to the same project.

---

## 🌐 Option C: Render.com

1. Create a **Web Service** for `backend` (Environment: Python 3, Build: `pip install -r requirements.txt`, Start: `gunicorn config.wsgi:application`).
2. Create a **Web Service** for `ml_service` (Build: `pip install -r requirements.txt`, Start: `gunicorn app:app`).
3. Create a **Managed PostgreSQL / MySQL** database.
4. Link the environment variables between the services.

---

## 🛠 Useful Production Maintenance Commands

| Task | Command |
|---|---|
| View live logs | `docker compose logs -f` |
| View backend logs | `docker compose logs -f backend` |
| View ML service logs | `docker compose logs -f ml_service` |
| Restart all services | `docker compose restart` |
| Run migrations | `docker compose exec backend python manage.py migrate` |
| Backup database | `docker compose exec db mysqldump -u finance_user -p finance_tracker > backup.sql` |
| Restore database | `docker compose exec -T db mysql -u finance_user -p finance_tracker < backup.sql` |
