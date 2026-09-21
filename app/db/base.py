"""
app/db/base.py — Alembic model registry.

WHY THIS FILE EXISTS:
    Alembic's autogenerate command inspects SQLModel.metadata to discover
    all table definitions. A table only appears in metadata AFTER its model
    class is imported into memory (Python's import system registers it on
    class creation via SQLModel's metaclass).

    If a model is NOT imported before Alembic runs, Alembic will:
      - MISS new tables during --autogenerate  (tables never created in DB)
      - DROP existing tables on the next migration (thinks they are extras)

    This file is the single authoritative import list.
    alembic/env.py imports this module, which triggers all model imports.

HOW TO ADD A NEW DOMAIN:
    1. Create your model in  app/domains/<name>/models.py
    2. Add an import line here:  import app.domains.<name>.models  # noqa: F401
    3. Run:  uv run alembic revision --autogenerate -m "add <name> tables"
    4. Run:  uv run alembic upgrade head
"""

# Core / Auth
import app.domains.auth.models  # noqa: F401  — User, Member, UserRole

# Campaigns
import app.domains.campaigns.models  # noqa: F401  — Campaign, CampaignStatus

# Donations (main + idempotency + receipts + pledges)
import app.domains.donations.models  # noqa: F401  — Donation, Receipt, Pledge, IdempotencyRecord

# Ledger (financial double-entry sub-domain of donations)
import app.domains.donations.ledger.models  # noqa: F401  — LedgerEntry

# Audit log (append-only)
import app.domains.audit.models  # noqa: F401  — AuditLog

# Webhooks (processed events / orphan guard)
import app.domains.webhooks.models  # noqa: F401  — ProcessedEvent
