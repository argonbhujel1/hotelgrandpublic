# Hotel Grand Garden — Public Website

**Domain:** https://hotelgrand.com.np  
**Shared DB:** same Aiven PostgreSQL as HMS (`hms.hotelgrand.com.np`)  
**Media:** Cloudinary  
**Host:** Vercel  

## Features
- Rooms & rates (synced from HMS `rooms` table)
- Restaurant menu (synced from HMS `menu_items`)
- Booked/occupied rooms list on restaurant page
- **QR order page** (`/qr/<token>`) — orders write to HMS `orders` table → Kitchen/POS
- Booking form, contact, location

## Local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional: copy .env.example → .env with DATABASE_URL
python run.py
```

## Vercel
1. New project from this repo
2. Env: `DATABASE_URL`, `SECRET_KEY`, Cloudinary keys, `PUBLIC_SITE_URL=https://hotelgrand.com.np`
3. Custom domain: `hotelgrand.com.np`

Use the **same** `DATABASE_URL` as HMS. Do not seed production DB from public site.
