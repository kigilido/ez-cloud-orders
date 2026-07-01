# Multi-Source Order Consolidation Platform
## Project Brief for Cursor AI

---

## 1. What This Project Is

An internal web application for an operator (a single worker or small team) that:

1. **Pulls orders** from multiple external sources (Zoho, SharePoint, Google Drive) into one normalized database on a recurring schedule.
2. **Lets the operator look up a customer by phone number**, see their eligibility status, and create an order in one click.
3. **Prevents duplicate orders** with an automatic warning system.
4. **Automates month-end billing** — generates invoices, pushes a consolidated statement to Zoho via API, and emails reports for SharePoint and Google Drive source orders.

This is an internal operator tool, not a customer-facing app. UI should be clean and functional, not complex.

---

## 2. Tech Stack — Final Decisions

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.14 | Best ecosystem for API integrations |
| Web framework | Django 5.x | Built-in admin, ORM, auth, no reinventing |
| Database | PostgreSQL | Reliable, handles JSON fields for flexible order data |
| Background jobs | Celery + Redis | Recurring sync tasks + month-end automation |
| Frontend | Django templates + HTMX | Internal tool — no need for React complexity |
| Styling | Tailwind CSS (CDN) | Fast, utility-first, no build step needed |
| Hosting | Railway (or Render) | Simple deploy from Git, managed PostgreSQL + Redis |
| Email | SendGrid or SMTP | For outbound invoice/statement emails |

---

## 3. Project Folder Structure

```
ez_cloud_orders/
├── manage.py
├── requirements.txt
├── .env.example
├── docker-compose.yml          # PostgreSQL + Redis for local dev
├── Dockerfile
│
├── config/                     # Django project settings
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/
│   ├── core/                   # Shared models, utilities, base classes
│   │   ├── models.py
│   │   └── utils.py
│   │
│   ├── customers/              # Customer/eligibility logic (Spruce list)
│   │   ├── models.py           # Customer, EligibilityRecord
│   │   ├── views.py            # Phone number search endpoint
│   │   ├── services.py         # Eligibility check logic
│   │   └── urls.py
│   │
│   ├── orders/                 # Order creation, duplicate detection, history
│   │   ├── models.py           # Order, OrderSource enum
│   │   ├── views.py            # Create order, order list, warnings
│   │   ├── services.py         # Order creation logic, duplicate check
│   │   └── urls.py
│   │
│   ├── connectors/             # One module per inbound source
│   │   ├── base.py             # Abstract BaseConnector class
│   │   ├── zoho.py             # Zoho API connector (OAuth2)
│   │   ├── sharepoint.py       # Microsoft Graph API connector
│   │   ├── google_drive.py     # Google Drive / Sheets API connector
│   │   └── sync_service.py     # Orchestrates all connector syncs
│   │
│   ├── billing/                # Month-end invoice + statement generation
│   │   ├── models.py           # Invoice, Statement
│   │   ├── services.py         # Generate invoices, push to Zoho, send emails
│   │   ├── tasks.py            # Celery task: run_month_end()
│   │   └── templates/
│   │       └── invoice.html    # Invoice HTML template for PDF generation
│   │
│   └── dashboard/              # Operator UI
│       ├── views.py            # Main search view, order creation view
│       ├── urls.py
│       └── templates/
│           └── dashboard/
│               ├── base.html
│               ├── search.html
│               ├── customer_card.html
│               └── order_confirm.html
│
└── templates/                  # Global templates
    └── base.html
```

---

## 4. Database Schema

### Customer (master eligibility list — sourced from Spruce)
```python
class Customer(models.Model):
    family_number       = models.CharField(max_length=20, unique=True)
    medicaid_id         = models.CharField(max_length=20, unique=True)
    first_name          = models.CharField(max_length=100)
    last_name           = models.CharField(max_length=100)
    address             = models.TextField()
    city_state_zip      = models.CharField(max_length=200)
    phone_number        = models.CharField(max_length=20, db_index=True)  # primary lookup key
    valid_until         = models.DateField()
    notes               = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    @property
    def is_eligible(self):
        return self.valid_until >= date.today()
```

### OrderSource (enum)
```python
class OrderSource(models.TextChoices):
    ZOHO         = 'zoho', 'Zoho'
    SHAREPOINT   = 'sharepoint', 'SharePoint'
    GOOGLE_DRIVE = 'google_drive', 'Google Drive'
    OTHER        = 'other', 'Other'
```

### InboundOrder (pulled from external sources)
```python
class InboundOrder(models.Model):
    source              = models.CharField(max_length=20, choices=OrderSource.choices)
    external_id         = models.CharField(max_length=200)   # ID in the source system
    customer            = models.ForeignKey(Customer, null=True, on_delete=models.SET_NULL)
    phone_number        = models.CharField(max_length=20)    # raw phone from source
    raw_data            = models.JSONField()                  # full source record
    synced_at           = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['source', 'external_id']          # prevents duplicate syncs
```

### Order (created by the operator — the outbound order)
```python
class Order(models.Model):
    customer            = models.ForeignKey(Customer, on_delete=models.PROTECT)
    inbound_order       = models.ForeignKey(InboundOrder, on_delete=models.PROTECT)
    source              = models.CharField(max_length=20, choices=OrderSource.choices)
    created_by          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    pos_order_id        = models.CharField(max_length=200, blank=True)   # ID returned by POS
    status              = models.CharField(max_length=20, default='pending')
    # billing
    invoice_number      = models.CharField(max_length=50, blank=True)
    billed_at           = models.DateTimeField(null=True)
```

### Invoice
```python
class Invoice(models.Model):
    order               = models.OneToOneField(Order, on_delete=models.PROTECT)
    invoice_number      = models.CharField(max_length=50, unique=True)
    generated_at        = models.DateTimeField(auto_now_add=True)
    pdf_file            = models.FileField(upload_to='invoices/')
    sent_at             = models.DateTimeField(null=True)
```

### MonthEndStatement
```python
class MonthEndStatement(models.Model):
    period_start        = models.DateField()
    period_end          = models.DateField()
    generated_at        = models.DateTimeField(auto_now_add=True)
    pushed_to_zoho_at   = models.DateTimeField(null=True)
    emailed_at          = models.DateTimeField(null=True)
    status              = models.CharField(max_length=20, default='pending')
    error_log           = models.TextField(blank=True)
```

---

## 5. Key Business Logic

### Eligibility Check
```
Customer is eligible if:
  1. Their phone number exists in the Customer table (Spruce list), AND
  2. Customer.valid_until >= today's date
```

### Duplicate Order Detection
```
Before creating an Order, check:
  SELECT COUNT(*) FROM orders_order
  WHERE customer_id = X
  AND created_at >= first_day_of_current_month
  
  If count > 0 → show warning, require operator confirmation to proceed
```

### Month-End Run (runs on last day of month at 11:59 PM)
```
1. Query all Orders for the month
2. Generate a PDF Invoice for each order
3. Generate one consolidated Statement PDF
4. Push statement to Zoho via API
5. Email invoices for SharePoint-sourced orders to [sharepoint_email]
6. Email invoices for Google Drive-sourced orders to [googledrive_email]
7. Mark MonthEndStatement as complete or log error
```

---

## 6. Source Connectors

Each connector implements a `sync()` method that returns a list of normalized records.

### Zoho Connector (`connectors/zoho.py`)
- Auth: OAuth2 (client_credentials or refresh token flow)
- Endpoint: GET `/crm/v3/[module]/search` (module TBD — awaiting client confirmation of Zoho product)
- Normalize: map Zoho fields → InboundOrder fields
- Store: upsert into InboundOrder using `external_id`

### SharePoint Connector (`connectors/sharepoint.py`)
- Auth: Microsoft Graph API (OAuth2, app registration in Azure)
- Endpoint: GET `/v1.0/sites/{site-id}/drive/items/{folder-id}/children`
- Download each file, parse content, normalize → InboundOrder
- Upsert using file ID as `external_id`

### Google Drive Connector (`connectors/google_drive.py`)
- Auth: Google Service Account (JSON key)
- API: Google Drive API v3 + Google Sheets API v4 (for spreadsheet files)
- List files in target folder, read sheet data, normalize → InboundOrder
- Upsert using file/row ID as `external_id`
- Known fields from sample: Family #, Medicaid ID, Last Name, First Name, Address, City/State/Zip, Phone, Valid Until, Date, Invoice #, Notes

### POS Connector (`connectors/pos_stub.py`)
- **Status: STUB** — POS system not yet confirmed by client
- The `create_order()` method logs to database and returns a placeholder ID
- Replace with real implementation once client confirms POS + API docs

---

## 7. Background Tasks (Celery)

```python
# Runs every 30 minutes — sync all sources
@app.task
def sync_all_sources():
    ZohoConnector().sync()
    SharePointConnector().sync()
    GoogleDriveConnector().sync()

# Runs on last day of month at 23:59
@app.task
def run_month_end():
    billing_service.run()
```

Celery beat schedule defined in `config/celery.py`.

---

## 8. Environment Variables (.env)

```
# Django
SECRET_KEY=
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost:5432/ez_cloud_orders
REDIS_URL=redis://localhost:6379/0

# Zoho
ZOHO_CLIENT_ID=
ZOHO_CLIENT_SECRET=
ZOHO_REFRESH_TOKEN=
ZOHO_ORG_ID=

# Microsoft (SharePoint)
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
SHAREPOINT_SITE_ID=
SHAREPOINT_FOLDER_ID=

# Google
GOOGLE_SERVICE_ACCOUNT_JSON=   # path to JSON key file

# Email (outbound)
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
SHAREPOINT_REPORT_EMAIL=
GOOGLE_DRIVE_REPORT_EMAIL=

# Billing
BILLING_DAY=last   # run month-end on last day of month
```

---

## 9. What to Build First (Phase Order)

**Phase 1 — Foundation**
- Django project scaffold, settings, docker-compose
- Customer model + import script (load the Spruce Excel file)
- Phone number search endpoint + eligibility check
- Basic operator UI (search page, customer card)

**Phase 2 — Connectors**
- Google Drive connector (sample file already available)
- SharePoint connector
- Zoho connector
- Sync scheduler (Celery beat)

**Phase 3 — Order Creation**
- Order model + duplicate detection
- "Create Order" button → POS stub (real POS wired in later)
- Operator confirmation flow with warnings

**Phase 4 — Billing**
- Invoice PDF generation
- Month-end statement
- Zoho push
- Email delivery

**Phase 5 — POS Integration**
- Wire in real POS once client confirms system and provides API docs

---

## 10. Open Items (Do Not Hard-Code These)

The following are still unconfirmed by the client. Build with these as configuration, not hardcoded values:

- POS system identity and API
- Zoho product (CRM / Books / Inventory) and target module for statement
- Fourth order source
- Invoice template / format
- Billing calculation logic (rate per order, per Medicaid ID, etc.)
- Recipient email addresses for month-end reports
- Monthly order volume (for pagination and rate-limit handling)
