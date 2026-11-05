# Dada Boys’ Wear Shop

## Local setup

From this directory, activate a virtual environment with Python 3.12 or newer,
install dependencies, and run migrations:

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/` for the shop and
`http://127.0.0.1:8000/admin/` to manage products and orders. Product stock
starts at zero; enter the real stock quantity in the admin before accepting
orders.

## Storefront

The storefront includes a featured product, searchable product cards, product
details, cart, checkout, order tracking, contact, and delivery/return
information pages. The category navigation menu links to actual products and
store information. The `/shop/` collection page has category, size, color, fit,
fabrication, embellishment, sleeve, item-segment, sale, and price filters, plus
sorting and responsive product cards. Add the real values and optional original
prices to each product in Django admin for the corresponding filters and sale
badges to appear. Create a separate product entry for each stocked size/color
combination so its stock and order details stay accurate. Shared responsive
styles and subtle reveal/hover animations live under `core/static/core/`;
animations respect the browser's
`prefers-reduced-motion` setting. Replace any sample product photos or text with
accurate store content from Django admin before launch.

## Orders and inventory

Checkout records an order and reserves the requested stock. Customers receive a
private tracking link and can open a prefilled WhatsApp message to confirm the
cash-on-delivery order. The customer must send that message; creating an order
does not send a WhatsApp message or collect payment automatically.

Use the order actions in Django admin to confirm, ship, deliver, or cancel
orders. Cancelling an open order restores its reserved stock. A tracking URL is
a private bearer link: share it only with that customer. The tracking page does
not show their phone number or delivery address.

## Production configuration

Set environment variables in the hosting platform; do not commit secrets:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<a newly generated secret>
DJANGO_ALLOWED_HOSTS=shop.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://shop.example.com
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False
WHATSAPP_PHONE=<country code and number, digits only>
```

Only enable HSTS for subdomains if every subdomain is also served over HTTPS.

Generate a secret locally with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

For PostgreSQL, also set `DJANGO_DB_ENGINE=django.db.backends.postgresql`,
`DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST`, and
`DJANGO_DB_PORT`. SQLite is the local-development default, not the recommended
database for a multi-worker production shop.

Before opening the production site:

1. Provision PostgreSQL and persistent media storage, and configure HTTPS.
2. Install the requirements and run `python manage.py migrate`.
3. Run `python manage.py collectstatic`.
4. Create an admin user, enter accurate stock, and verify the WhatsApp number.
5. Run `python manage.py check --deploy` with the production environment.

The project is not deployed by these instructions. Configure the hosting
provider to serve `staticfiles` and persistent `media` files, and use its
recommended Django application server and database backups.
