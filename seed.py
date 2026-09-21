"""
seed.py — One-command database seed script for GiveNaija API.
Sets up demo accounts, sample campaigns, and an initial verified donation with receipt.
Idempotent: Safe to run multiple times without creating duplicate records.
"""
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.core.security import hash_password
from app.db.session import engine, init_db
from app.domains.audit.models import AuditLog
from app.domains.audit.service import AuditService
from app.domains.auth.models import Member, User, UserRole
from app.domains.campaigns.models import Campaign, CampaignStatus
from app.domains.donations.models import Donation, Receipt


def seed_database() -> None:
    print("[*] Initializing GiveNaija database schema and append-only triggers...")
    init_db()
    try:
        AuditService.enforce_append_only_rules(engine)
    except Exception as e:
        print(f"Trigger notice: {e}")

    with Session(engine) as session:
        print("[*] Creating demo users...")

        # 1. Admin Account
        admin = session.exec(
            select(User).where(User.email == "admin@givenaija.org")
        ).first()
        if not admin:
            admin = User(
                email="admin@givenaija.org",
                password_hash=hash_password("Admin123!"),
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            session.add(admin)
            session.flush()
            session.add(
                AuditLog(
                    actor_id=admin.id,
                    action="SEED_USER_CREATED",
                    target_type="users",
                    target_id=admin.id,
                    details="Seeded Admin account",
                )
            )
            print("   -> Created Admin: admin@givenaija.org / Admin123!")
        else:
            print("   -> Admin already exists.")

        # 2. Finance Officer Account
        finance = session.exec(
            select(User).where(User.email == "finance@givenaija.org")
        ).first()
        if not finance:
            finance = User(
                email="finance@givenaija.org",
                password_hash=hash_password("Finance123!"),
                role=UserRole.FINANCE.value,
                is_active=True,
            )
            session.add(finance)
            session.flush()
            session.add(
                AuditLog(
                    actor_id=admin.id,
                    action="SEED_USER_CREATED",
                    target_type="users",
                    target_id=finance.id,
                    details="Seeded Finance Officer account",
                )
            )
            print("   -> Created Finance Officer: finance@givenaija.org / Finance123!")
        else:
            print("   -> Finance Officer already exists.")

        # 3. Donor Account
        donor = session.exec(
            select(User).where(User.email == "donor@givenaija.org")
        ).first()
        if not donor:
            donor = User(
                email="donor@givenaija.org",
                password_hash=hash_password("Donor123!"),
                role=UserRole.DONOR.value,
                is_active=True,
            )
            session.add(donor)
            session.flush()

            # Member profile
            member = Member(
                user_id=donor.id,
                phone="+2348012345678",
            )
            session.add(member)
            session.flush()

            session.add(
                AuditLog(
                    actor_id=donor.id,
                    action="SEED_USER_CREATED",
                    target_type="users",
                    target_id=donor.id,
                    details="Seeded Donor account and Member profile",
                )
            )
            print("   -> Created Donor: donor@givenaija.org / Donor123!")
        else:
            member = session.exec(
                select(Member).where(Member.user_id == donor.id)
            ).first()
            print("   -> Donor already exists.")

        print("[*] Creating sample fundraising campaigns...")
        # Campaign 1: Open
        c1 = session.exec(
            select(Campaign).where(Campaign.title == "Borehole for Ikot Ekpene")
        ).first()
        if not c1:
            c1 = Campaign(
                title="Borehole for Ikot Ekpene",
                description="Providing clean drinking water to over 5,000 community residents.",
                goal_amount=200000000,  # 2,000,000 NGN
                raised_amount=0,
                status=CampaignStatus.OPEN.value,
            )
            session.add(c1)
            session.flush()
            session.add(
                AuditLog(
                    actor_id=admin.id,
                    action="SEED_CAMPAIGN_CREATED",
                    target_type="campaigns",
                    target_id=c1.id,
                    details="Seeded open campaign: Borehole for Ikot Ekpene",
                )
            )
            print("   -> Created Campaign: Borehole for Ikot Ekpene (Open)")

        # Campaign 2: Open
        c2 = session.exec(
            select(Campaign).where(Campaign.title == "Lagos Orphanage Education Drive")
        ).first()
        if not c2:
            c2 = Campaign(
                title="Lagos Orphanage Education Drive",
                description="School fees, books, and uniforms for 120 children.",
                goal_amount=500000000,  # 5,000,000 NGN
                raised_amount=0,
                status=CampaignStatus.OPEN.value,
            )
            session.add(c2)
            session.flush()
            session.add(
                AuditLog(
                    actor_id=admin.id,
                    action="SEED_CAMPAIGN_CREATED",
                    target_type="campaigns",
                    target_id=c2.id,
                    details="Seeded open campaign: Lagos Orphanage Education Drive",
                )
            )
            print("   -> Created Campaign: Lagos Orphanage Education Drive (Open)")

        # Campaign 3: Closed
        c3 = session.exec(
            select(Campaign).where(Campaign.title == "Enugu Medical Outreach 2025")
        ).first()
        if not c3:
            c3 = Campaign(
                title="Enugu Medical Outreach 2025",
                description="Past community medical screening and prescription giveaway.",
                goal_amount=150000000,  # 1,500,000 NGN
                raised_amount=150000000,
                status=CampaignStatus.CLOSED.value,
            )
            session.add(c3)
            session.flush()
            session.add(
                AuditLog(
                    actor_id=admin.id,
                    action="SEED_CAMPAIGN_CREATED",
                    target_type="campaigns",
                    target_id=c3.id,
                    details="Seeded closed campaign: Enugu Medical Outreach 2025",
                )
            )
            print("   -> Created Campaign: Enugu Medical Outreach 2025 (Closed)")

        # Initial verified demo donation
        bank_ref = "TXN-INIT-DEMO-001"
        existing_donation = session.exec(
            select(Donation).where(Donation.bank_ref == bank_ref)
        ).first()
        if not existing_donation and c1:
            donation = Donation(
                campaign_id=c1.id,
                member_id=member.id if member else None,
                amount=5000000,  # 50,000 NGN
                bank_ref=bank_ref,
                recorded_by=finance.id,
                at=datetime.now(timezone.utc),
            )
            session.add(donation)
            session.flush()

            c1.raised_amount += donation.amount
            session.add(c1)

            receipt = Receipt(
                donation_id=donation.id,
                number="RCPT-000001-DEMO",
                issued_at=datetime.now(timezone.utc),
            )
            session.add(receipt)

            session.add(
                AuditLog(
                    actor_id=finance.id,
                    action="SEED_DONATION_RECORDED",
                    target_type="donations",
                    target_id=donation.id,
                    details=f"Initial seeded donation of {donation.amount} kobo",
                )
            )

            from decimal import Decimal
            from app.domains.donations.ledger.models import LedgerEntry, EntryType

            ledger_entry = LedgerEntry(
                donation_id=donation.id,
                campaign_id=c1.id,
                entry_type=EntryType.CREDIT,
                amount_ngn=Decimal(donation.amount) / Decimal(100),
                description=f"Seeded demo donation {donation.bank_ref}",
                recorded_at=datetime.now(timezone.utc),
            )
            session.add(ledger_entry)

            print("   -> Created verified demo donation, ledger entry, and receipt: RCPT-000001-DEMO")

        session.commit()
        print("\n[OK] Seeding complete! Database is ready for demo and automated testing.")


if __name__ == "__main__":
    seed_database()
