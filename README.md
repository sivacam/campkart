# CAMPKART MVP

A professional mobile-first college marketplace for verified students to **Buy, Sell, and Rent** items within campus.

## Features
- Student registration/login
- Configurable college email domain
- Student verification status
- Buy / Sell / Rent listings
- Rental rates: day / week / month
- Search and category filters
- Product detail pages
- Reservation workflow
- Seller dashboard
- Report listing
- Admin dashboard for verification, listing moderation, and reports
- 10% platform commission calculation
- Responsive green/white CAMPKART UI

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Configuration

Optional environment variables:
- `SECRET_KEY` – production secret
- `COLLEGE_DOMAIN` – e.g. `yourcollege.edu.in`. Leave blank to allow any email during prototype testing.
- `ADMIN_EMAIL` – admin account email (default: `admin@campkart.local`)
- `ADMIN_PASSWORD` – admin password (default: `ChangeMe123!`)

## Important production work before launch
- Use PostgreSQL instead of SQLite
- Use a real email/college SSO verification flow
- Add a proper payment gateway and webhook verification
- Add cloud image storage
- Add rate limiting, CSRF protection, security headers, audit logs, and backups
- Add privacy policy, terms, refund/rental rules, and moderation policy
- Never store unnecessary ID-card images or sensitive student data
