# ChicCherry — E-Commerce Platform

A full-featured Django e-commerce web application for fashion and lifestyle products, built for the Bangladesh market.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2.6, Python 3.13 |
| Database | SQLite (dev) / PostgreSQL (prod via RDS) |
| Frontend | Bootstrap 4, jQuery, Font Awesome 6 |
| Email | Node.js Nodemailer service (port 3001) + Django SMTP fallback |
| Storage | Local filesystem / MinIO (optional, S3-compatible) |
| Auth | Custom `AbstractBaseUser` (email-based) with OTP verification |
| Session | `django-session-timeout` (1-hour expiry, separate admin session cookie) |

---

## Project Structure

```
web+finalyearproject/
├── accounts/        # Custom user auth, profiles, OTP
├── carts/           # Cart, orders, payments, OTP checkout
├── category/        # Product categories
├── store/           # Products, variations, reviews, gallery, site settings
├── ecommerce/       # Primary Django config (settings, urls, views, templates)
├── greatkart/       # Secondary config (MinIO, RDS, custom admin site)
├── templates/       # Global templates (admin dashboard, home)
├── static/          # CSS, JS, images, fonts
├── media/           # Uploaded files (products, profiles, slider)
├── emailService.js  # Node.js Nodemailer microservice
├── email_utils.py   # Python helper to call the Node.js service
├── start.bat        # Starts both email service and Django together
└── manage.py
```

---

## Apps Overview

### `accounts`
- Custom `Account` model (email-based login, `AbstractBaseUser`)
- `UserProfile` with address and profile picture
- OTP-based registration verification (10-minute expiry) + resend OTP
- Password reset via email token (`uidb64` / `token`)
- Dashboard, edit profile, change password, order history, order detail

### `store`
- `Product` with slug, image, stock, category, `discount_percent`
- `discounted_price` property (computed from `discount_percent`)
- `ProductGallery` for multiple product images
- `VariationCategory` (admin-managed: color, size, etc.)
- `Variation` linked to products via ForeignKey + `VariationManager`
- `ReviewRating` with image upload, purchase verification, moderation (`is_visible`)
- `ReviewAudit` trail for admin approve/reject/edit actions
- `HelpfulnessVote` per review per user (unique together)
- `FooterSettings` singleton — logo, contact info, payment icon toggles, header email/phone
- `PaymentMethod` — admin-managed list with FontAwesome icon class
- `SliderItem` — home page slider supporting both images and videos

### `carts`
- Session-based and user-linked `Cart` / `CartItem`
- Cart merges on login
- `Order` with full shipping details, `email_verified` flag, `payment_status`
- `OrderItem` with variation tracking
- `OrderStatusUpdate` history log with notes
- `OTP` model for checkout email verification (6-digit, 10-minute expiry)
- `PaymentAccount` saved per user per method (masked display)
- Payment methods: Visa, Mastercard, Rocket, bKash, Upay, Nogod

### `category`
- `Category` with slug and image
- Used for product filtering and navbar dropdown

---

## Settings Configurations

| File | Purpose |
|---|---|
| `ecommerce/settings.py` | Primary dev settings (hardcoded secrets, SQLite) |
| `ecommerce/settings_store.py` | Extends primary; overrides `ROOT_URLCONF` to `ecommerce.urls_store` |
| `greatkart/settings.py` | Secondary config with `python-decouple`, MinIO, RDS support |

The active settings module used by `start.bat` and `manage.py runserver` is `ecommerce.settings_store`.

---

## Setup & Installation

```bash
# 1. Clone the repo
git clone <repo-url>
cd web+finalyearproject

# 2. Create and activate virtual environment
python -m venv env
env\Scripts\activate        # Windows
source env/bin/activate     # macOS/Linux

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Node.js dependencies (for email service)
npm install

# 5. Apply migrations
python manage.py migrate --settings=ecommerce.settings_store

# 6. Create superuser
python manage.py createsuperuser --settings=ecommerce.settings_store

# 7. Run everything (email service + Django)
start.bat                   # Windows — opens two terminal windows
# OR manually:
node emailService.js        # Terminal 1
python manage.py runserver 8000 --settings=ecommerce.settings_store  # Terminal 2
```

---

## Key URLs

| URL | Description |
|---|---|
| `/` | Home page with slider |
| `/store/` | Product listing with filters |
| `/store/discounts/` | Discounted products |
| `/store/search/` | Product search |
| `/store/<category>/` | Products by category |
| `/store/<category>/<product>/` | Product detail |
| `/cart/` | Shopping cart |
| `/cart/checkout/` | Checkout with OTP email verification |
| `/cart/send_otp/` | AJAX endpoint to send checkout OTP |
| `/cart/payment/<id>/` | Payment method selection |
| `/cart/confirm_payment/<id>/` | Confirm payment |
| `/cart/confirmation/<id>/` | Order confirmation |
| `/cart/visa_payment/<id>/` | Visa payment page |
| `/cart/bkash_payment/<id>/` | bKash payment page |
| `/cart/rocket_payment/<id>/` | Rocket payment page |
| `/cart/mastercard_payment/<id>/` | Mastercard payment page |
| `/cart/upay_payment/<id>/` | Upay payment page |
| `/cart/nogod_payment/<id>/` | Nogod payment page |
| `/accounts/register/` | User registration |
| `/accounts/login/` | User login |
| `/accounts/verify_otp/` | OTP verification after registration |
| `/accounts/dashboard/` | User dashboard |
| `/accounts/my_orders/` | Order history |
| `/accounts/order_detail/<id>/` | Order detail |
| `/accounts/edit_profile/` | Edit profile |
| `/accounts/change_password/` | Change password |
| `/accounts/forgotPassword/` | Password reset request |
| `/secureadmin/` | Admin dashboard |

---

## Admin Features

- Custom `ChicCherryAdminSite` (`site_header = "ChicCherry"`)
- Dashboard stat cards: total orders, products, users, revenue
- Monthly revenue chart (last 12 months) + recent orders table (last 8)
- Separate admin session cookie (`adminid`) — admin login does not affect store session
- Product inline: multiple variations (dynamic categories) + multiple gallery images
- Review moderation: approve/reject with `ReviewAudit` trail
- `FooterSettings` singleton editable from admin
- `SliderItem` management (image/video, order, duration, caption)
- `PaymentMethod` management
- "View Store" button opens store in preview mode

---

## Email Service

`emailService.js` runs as an Express server on port `3001`. Django calls it via `email_utils.py` (`send_email_via_nodemailer`). If the Node.js service is unavailable, Django falls back to its configured SMTP backend.

Emails sent for:
- Account OTP verification
- Checkout OTP verification
- Order confirmation
- Review submission confirmation
- Password reset

---

## Environment Variables

Create a `.env` file in the project root (used by `greatkart/settings.py` via `python-decouple`):

```env
SECRET_KEY=<your-django-secret-key>
DEBUG=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=<email>
EMAIL_HOST_PASSWORD=<app-password>
EMAIL_USE_TLS=True
USE_MINIO=False
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=greatkart-media
MINIO_USE_HTTPS=False
```

For AWS RDS (PostgreSQL), set `RDS_DB_NAME`, `RDS_USERNAME`, `RDS_PASSWORD`, `RDS_HOSTNAME`, `RDS_PORT` as environment variables.

---

## Dependencies

### Python (`requirements.txt`)
```
Django==5.2.6
Pillow==11.3.0
requests==2.32.5
stripe==8.0.0
minio==7.2.7
django-storages==1.14.4
sslcommerz-python==0.0.7
django-session-timeout
python-decouple
```

### Node.js (`package.json`)
```
express, nodemailer, cors, dotenv
```
Dev: `nodemon`, `concurrently`
