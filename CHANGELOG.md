# Changelog
All notable changes to **QR Support App** will be documented in this file.  
This project follows [Semantic Versioning](https://semver.org/).


## [v0.5.0] - 2025-09-25
### Added
- **Emailer pipeline**:
  - New utility (`emailer.py`) with rendering + sending support emails.
  - Jinja2 templates for subject and body (`subject.j2`, `body.txt.j2`, `body.html.j2`), bilingual EN/FR by default.
  - Emails now include machine type/serial and operator details.
  - Fallback to `.eml` files in `.outbox/` when `EMAIL_ENABLED=false` (local dev mode).
- **Observability**:
  - Extended `EmailLog` model with `status`, `provider_message_id`, `error`, and `payload_hash`.
  - New Alembic migration `40337e53cf25_add_email_log_observability_fields.py`.
  - Audit events for email send failures.
- **Settings**:
  - Added SMTP configuration (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_STARTTLS`, `MAIL_FROM`, `EMAIL_ENABLED`) to `.env.example`.

### Changed
- **Public form submission**:
  - After ticket creation, emails are automatically sent and logged.
  - User-facing flow remains the same (always shows success), while errors are recorded internally.

---

## [v0.4.0] - 2025-09-24
### Added
- **Admin QR Generator**:
  - Generate public support form URLs directly from admin panel.
  - Inline QR code PNG preview with option to download (`{type}_{serial}.png`).
  - Audit event logging for QR code generation.
- **Public form prefill**:
  - `/public/form` now accepts `machine_type` and `machine_serial` query params.
  - Automatically fills form fields when reached from QR code.
- **Settings**:
  - Switched from `ADMIN_PASS` → `ADMIN_PASS_HASH` (bcrypt).
  - Added `SESSION_MAX_AGE_MIN` configurable session lifetime.

---

## [v0.3.0] - 2025-09-01
### Added
- **Admin interface**:
  - Login/logout with CSRF, sessions, flash messages, and audit events.
  - Rate limiting on login attempts.
  - Dashboard placeholder.
- **Basic security**:
  - CSRF protection on forms.
  - Honeypot anti-bot field in public form.
- **Session management**:
  - Signed cookies with expiration and secure flags.

---

## [v0.2.0] - 2025-08-29
### Added
- **Scaffolding**:
  - Database models: `Machine`, `Ticket`, `QRToken`, `EmailLog`, `AuditEvent`.
  - Alembic migrations.
  - Core project structure with FastAPI + SQLAlchemy + Jinja2.
  - Environment variables support via `python-dotenv`.

---

## [v0.1.0] - 2025-08-29
### Added
- **Initial setup**:
  - FastAPI app with Uvicorn.
  - Base folder structure (`app/main.py`, `routes/`, `templates/`, `utils/`).
  - Public `/form` endpoint with validation, ticket creation, and DB insert.
  - Email + audit logging placeholders.
  - SQLite (dev) → PostgreSQL (prod) compatibility.

---

