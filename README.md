# OCI Cloud Activation

Automated OCI Resource Manager stack deployment scheduler built with Django.  
Attempts to provision a **VM.Standard.A1.Flex** instance at scheduled intervals until capacity is available.

## How It Works

1. **Scheduler** runs at **6:00 AM · 9:00 AM · 7:00 PM · 11:00 PM IST**
2. Each run executes: **Plan** → **Apply** → **Email** → **Stop**
3. On successful apply, sends a notification via Brevo and stops all future attempts
4. Dashboard at `/` shows live status, countdown timer, and job history

## Stack

- **Django** — Web framework  
- **APScheduler** — Background cron scheduler  
- **OCI Python SDK** — Oracle Cloud Infrastructure API  
- **Brevo API** — Transactional email  
- **WhiteNoise** — Static file serving  
- **Gunicorn** — Production WSGI server  

## Deployment

Hosted on [Render](https://render.com) → `req-oci-cloud.onrender.com`

Set environment variables on Render (see `render.yaml` for the full list).

```bash
./build.sh          # Install deps, collect static, migrate
gunicorn oci_cloud_project.wsgi:application --preload
```

## Local Development

```bash
python -m venv env && source env/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in your secrets
python manage.py migrate
python manage.py runserver
```
