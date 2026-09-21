"""
generate_study_guide_pdf.py — Generates a comprehensive, beautifully styled PDF
study guide for the GiveNaija NGO Backend Capstone presentation.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Adds 'Page X of Y' and header to all pages dynamically."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        
        # Header (on pages 2 and later)
        if self._pageNumber > 1:
            self.drawString(36, 762, "GiveNaija NGO Backend — Comprehensive Presentation Study Guide")
            self.drawRightString(letter[0] - 36, 762, "Team Mighty Spark")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(36, 755, letter[0] - 36, 755)

        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 36, 25, footer_text)
        self.drawString(36, 25, "Confidential — Backend Capstone Defense Study Guide")
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(36, 35, letter[0] - 36, 35)
        
        self.restoreState()


def create_pdf(filename="GiveNaija_Capstone_Study_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#1A365D")    # Deep Navy
    SECONDARY = colors.HexColor("#2B6CB0")  # Royal Blue
    ACCENT = colors.HexColor("#2E7D32")     # NGO Emerald Green
    DARK_TEXT = colors.HexColor("#2D3748")  # Charcoal
    LIGHT_BG = colors.HexColor("#F7FAFC")   # Soft Off-White
    BORDER_COLOR = colors.HexColor("#E2E8F0")
    ALERT_BG = colors.HexColor("#FEF3C7")   # Amber tint
    ALERT_BORDER = colors.HexColor("#D97706")

    # Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        alignment=1, # Centered
        spaceAfter=10,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=SECONDARY,
        alignment=1,
        spaceAfter=20,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=DARK_TEXT,
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#805AD5"),
        spaceAfter=4,
    )

    callout_style = ParagraphStyle(
        "Callout_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#92400E"),
    )

    qa_q_style = ParagraphStyle(
        "QA_Question",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=PRIMARY,
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True,
    )

    qa_a_style = ParagraphStyle(
        "QA_Answer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=DARK_TEXT,
        leftIndent=12,
        spaceAfter=6,
    )

    story = []

    def make_callout(text, title="KEY TAKEAWAY FOR EXAMINERS"):
        content = [
            Paragraph(f"<b>{title}:</b> {text}", callout_style)
        ]
        t = Table([[content]], colWidths=[540])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ALERT_BG),
            ('BOX', (0,0), (-1,-1), 1, ALERT_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        return t

    # ---------------------------------------------------------
    # COVER / HEADER
    # ---------------------------------------------------------
    story.append(Spacer(1, 15))
    story.append(Paragraph("GiveNaija NGO — Backend Capstone", title_style))
    story.append(Paragraph("Line-by-Line Technical Explanation & Presentation Defense Study Guide<br/><b>Team Mighty Spark (Victor & Anthony) | Product 10: NGO Donations & Members</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceBefore=0, spaceAfter=12))

    # Executive Overview
    story.append(Paragraph("1. Executive Summary & The Capstone Hard Problem", h1_style))
    story.append(Paragraph(
        "GiveNaija is a mission-driven backend system engineered for Nigerian NGOs to manage fundraising campaigns, "
        "track donors and memberships, accept bank and gateway payments, and maintain an immutable financial ledger.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Capstone Hard Problem:</b> <i>\"Record every Naira exactly once, with an audit trail nobody can edit.\"</i>",
        body_style
    ))
    story.append(Paragraph(
        "In regular software, race conditions, retried webhooks, or rogue admin queries can cause duplicate donation counts "
        "or altered records. In GiveNaija, exact-once integrity is enforced across <b>five unbreakable layers</b>:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>Layer 1 (Database Constraint):</b> <code>bank_ref UNIQUE</code> on the <code>donations</code> table guarantees that the database engine rejects duplicate transactions at the disk level.", bullet_style))
    story.append(Paragraph("&bull; <b>Layer 2 (Concurrency Trap):</b> <code>IntegrityError</code> is caught in the Python service and returns HTTP 409 Conflict if two bank webhooks arrive at the exact same millisecond.", bullet_style))
    story.append(Paragraph("&bull; <b>Layer 3 (Idempotency Key Cache):</b> The <code>Idempotency-Key</code> HTTP header caches the original 201 response. Retrying returns the original response with HTTP 200 without executing the transaction again.", bullet_style))
    story.append(Paragraph("&bull; <b>Layer 4 (Database Triggers):</b> PostgreSQL/SQLite C-level triggers block any SQL <code>UPDATE</code> or <code>DELETE</code> command executed against the <code>audit_log</code> table.", bullet_style))
    story.append(Paragraph("&bull; <b>Layer 5 (HMAC-SHA256 Webhook Verification):</b> Incoming webhooks are rejected with HTTP 401 unless signed with a cryptographic HMAC matching the shared payment gateway secret.", bullet_style))

    story.append(Spacer(1, 4))
    story.append(make_callout(
        "When the examiner asks 'How do you prevent double counting?', explain that you do NOT rely on application logic alone; "
        "you combine an application-level Idempotency-Key cache with a database-level UNIQUE constraint on bank_ref.",
        "EXAMINER DEFENSE TIP"
    ))
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # ARCHITECTURE & TECH STACK
    # ---------------------------------------------------------
    story.append(Paragraph("2. System Architecture & Why Each Technology Was Chosen", h1_style))
    
    tech_data = [
        [Paragraph("<b>Component</b>", body_style), Paragraph("<b>Technology</b>", body_style), Paragraph("<b>Why It Was Chosen (Architectural Rationale)</b>", body_style)],
        [Paragraph("<b>Framework</b>", body_style), Paragraph("FastAPI", code_style), Paragraph("Asynchronous ASGI performance, automatic OpenAPI / Swagger generation, Pydantic type validation.", body_style)],
        [Paragraph("<b>Database</b>", body_style), Paragraph("PostgreSQL 16 (Docker)", code_style), Paragraph("Strict ACID compliance, row-level locking, foreign keys, and stored PL/pgSQL trigger functions.", body_style)],
        [Paragraph("<b>ORM & Validation</b>", body_style), Paragraph("SQLModel & Pydantic v2", code_style), Paragraph("Combines SQLAlchemy ORM with Pydantic validation into a single class, avoiding duplicate schemas.", body_style)],
        [Paragraph("<b>Migrations</b>", body_style), Paragraph("Alembic", code_style), Paragraph("Version-controlled database schema changes. Auto-detects model differences and runs on app startup.", body_style)],
        [Paragraph("<b>Cache & Limits</b>", body_style), Paragraph("Redis 7 (Docker)", code_style), Paragraph("Sub-millisecond campaign caching and high-speed sliding window rate-limiting for auth endpoints.", body_style)],
        [Paragraph("<b>Live Streaming</b>", body_style), Paragraph("Server-Sent Events (SSE)", code_style), Paragraph("Unidirectional real-time donation ticker. 10x lighter than WebSockets, handles auto-reconnect natively.", body_style)],
        [Paragraph("<b>Testing Stack</b>", body_style), Paragraph("Pytest + TestClient", code_style), Paragraph("31 automated tests with an isolated in-memory SQLite fixture and coverage tracking.", body_style)],
    ]
    t_tech = Table(tech_data, colWidths=[90, 110, 340])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_tech)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # DIRECTORY STRUCTURE BREAKDOWN
    # ---------------------------------------------------------
    story.append(Paragraph("3. Complete Codebase Tour: Line-by-Line / File-by-File", h1_style))
    story.append(Paragraph("The codebase follows a strict <b>Domain-Driven Layered Architecture</b>. High-level HTTP routers delegate to business service layers, which interact with database models inside atomic transactions.", body_style))

    story.append(Paragraph("A. Application Core (app/core/)", h2_style))
    story.append(Paragraph("&bull; <b>config.py:</b> Implements 12-Factor config using <code>pydantic_settings.BaseSettings</code>. Reads environment variables (JWT secrets, PostgreSQL connection strings, Redis URLs) with sensible fallback defaults. Prevents hardcoding secrets in code.", bullet_style))
    story.append(Paragraph("&bull; <b>security.py:</b> Houses cryptographic functions: <code>hash_password()</code> and <code>verify_password()</code> using bcrypt; <code>create_access_token()</code> encoding JWT with expiration timestamps; and <code>verify_webhook_signature()</code> performing constant-time HMAC-SHA256 verification (preventing timing attacks).", bullet_style))
    story.append(Paragraph("&bull; <b>deps.py:</b> Reusable FastAPI dependencies. Decodes the JWT Bearer token, queries the active user, and enforces Role-Based Access Control (RBAC) through <code>require_role()</code>, <code>require_admin</code>, <code>require_finance</code>, and <code>require_donor</code>.", bullet_style))
    story.append(Paragraph("&bull; <b>errors.py:</b> Custom <code>AppException</code> class and global exception handlers. Converts unhandled exceptions into a uniform JSON envelope: <code>{\"error\": {\"code\": \"...\", \"message\": \"...\", \"request_id\": \"...\"}}</code> so clients never receive raw 500 HTML tracebacks.", bullet_style))
    story.append(Paragraph("&bull; <b>middleware.py:</b> Two custom ASGI middlewares: <code>RequestLoggingAndTimingMiddleware</code> attaches a unique UUID <code>X-Request-ID</code> and measures execution time in <code>X-Process-Time</code>; <code>RateLimiterMiddleware</code> enforces 5 login attempts/min using Redis with a 429 response and <code>Retry-After</code> header.", bullet_style))
    story.append(Paragraph("&bull; <b>broadcaster.py:</b> In-memory event broadcaster using Python's <code>asyncio.Queue</code>. When a donation occurs, it pushes an event to all connected SSE clients subscribed to that specific campaign without database polling.", bullet_style))
    story.append(Paragraph("&bull; <b>idempotency.py:</b> Core idempotency module providing <code>check_idempotency_key()</code> and <code>store_idempotency_response()</code> to ensure safe retries.", bullet_style))

    story.append(Paragraph("B. Database Engine & Migrations (app/db/)", h2_style))
    story.append(Paragraph("&bull; <b>session.py:</b> Creates the SQLModel SQLAlchemy engine. Points to PostgreSQL on Docker (port 5433) and gracefully falls back to local SQLite if Docker is temporarily offline. Provides the <code>get_db()</code> dependency yielding a clean database session per request.", bullet_style))
    story.append(Paragraph("&bull; <b>base.py:</b> The central model registry. Explicitly imports every domain model into memory so that <code>SQLModel.metadata</code> contains all tables before Alembic runs autogenerate.", bullet_style))
    story.append(Paragraph("&bull; <b>migrations.py:</b> Programmatic migration runner. Invokes <code>alembic.command.upgrade(cfg, 'head')</code> during app startup so production schemas are always up to date automatically.", bullet_style))
    story.append(Paragraph("&bull; <b>redis.py:</b> High-speed caching client. Provides <code>get_cache()</code>, <code>set_cache()</code>, and pattern-based <code>invalidate_cache()</code>. Campaign listing queries are cached for 60 seconds and instantly purged upon new donations.", bullet_style))
    story.append(Paragraph("&bull; <b>firestore.py:</b> Syncs donation events and activity feeds to Google Cloud Firestore with automatic graceful fallback if GCP credentials are not configured.", bullet_style))

    story.append(PageBreak()) # Clean page break for Domains

    story.append(Paragraph("C. Business Domains (app/domains/)", h2_style))
    story.append(Paragraph("Each business domain is self-contained with its own <code>models.py</code>, <code>schemas.py</code>, <code>service.py</code>, and <code>router.py</code>.", body_style))

    # Domain Table
    domain_data = [
        [Paragraph("<b>Domain</b>", body_style), Paragraph("<b>Key Models & Endpoints</b>", body_style), Paragraph("<b>Critical Business Rules Implemented</b>", body_style)],
        [
            Paragraph("<b>auth/</b>", body_style),
            Paragraph("User, Member<br/>POST /auth/register<br/>POST /auth/login", code_style),
            Paragraph("Registers users with bcrypt hashes. If role is DONOR, atomically generates a Member profile with phone and member_code. Emits JWT bearer token upon valid login.", body_style)
        ],
        [
            Paragraph("<b>campaigns/</b>", body_style),
            Paragraph("Campaign<br/>GET /campaigns<br/>POST /campaigns<br/>GET /campaigns/{id}/stream", code_style),
            Paragraph("Campaigns track goal_amount and raised_amount. Cached in Redis. Provides an SSE endpoint (<code>/stream</code>) that streams live donations to frontend dashboards in real time.", body_style)
        ],
        [
            Paragraph("<b>donations/</b>", body_style),
            Paragraph("Donation, Receipt, Pledge<br/>POST /donations<br/>GET /donations/me<br/>GET /receipts/{id}", code_style),
            Paragraph("Records bank donations. Enforces closed-campaign checks (rejects closed campaigns with 409). Generates immutable numbered receipts (RCPT-XXXXXX) exactly once per donation.", body_style)
        ],
        [
            Paragraph("<b>donations/ledger/</b>", body_style),
            Paragraph("LedgerEntry<br/>GET /ledger/campaign/{id}<br/>GET /ledger/campaign/{id}/verify", code_style),
            Paragraph("Double-entry financial accounting layer. Every donation creates a CREDIT row. Verification endpoint sums ledger CREDITs and confirms it matches campaigns.raised_amount.", body_style)
        ],
        [
            Paragraph("<b>audit/</b>", body_style),
            Paragraph("AuditLog<br/>GET /admin/audit-log", code_style),
            Paragraph("Records every mutating operation (who, action, target, timestamp, details). Protected by DB-level append-only triggers. Only accessible by ADMIN role.", body_style)
        ],
        [
            Paragraph("<b>webhooks/</b>", body_style),
            Paragraph("ProcessedEvent<br/>POST /webhooks/payment", code_style),
            Paragraph("Handles payment gateway webhooks. Verifies HMAC-SHA256 signature. Deduplicates event_id. If bank reference is unrecognized, marks event as orphan and logs it without crashing.", body_style)
        ],
    ]
    t_domain = Table(domain_data, colWidths=[75, 175, 290])
    t_domain.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_domain)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # CRITICAL WORKFLOWS
    # ---------------------------------------------------------
    story.append(Paragraph("4. Step-by-Step Execution of Core Workflows", h1_style))

    story.append(Paragraph("Workflow 1: Recording a Donation (The Atomic Transaction)", h2_style))
    story.append(Paragraph(
        "When an officer records a donation via <code>POST /donations</code>, the following <b>six steps occur inside a single atomic transaction</b>:",
        body_style
    ))
    story.append(Paragraph("1. <b>Validation:</b> Verify user has <code>FINANCE</code> or <code>ADMIN</code> role. Verify campaign is <code>OPEN</code> (if closed, raise 409).", bullet_style))
    story.append(Paragraph("2. <b>Idempotency Check:</b> If <code>Idempotency-Key</code> header is provided and was already processed, return stored response immediately.", bullet_style))
    story.append(Paragraph("3. <b>Insert Donation Row:</b> Insert into <code>donations</code> with <code>bank_ref</code>. If a race condition occurs, <code>bank_ref UNIQUE</code> throws an IntegrityError.", bullet_style))
    story.append(Paragraph("4. <b>Update Campaign Total:</b> Increment <code>campaign.raised_amount += amount</code>.", bullet_style))
    story.append(Paragraph("5. <b>Insert Financial Ledger Entry:</b> Insert immutable row into <code>ledger_entries</code> with <code>amount_ngn</code> and <code>entry_type=CREDIT</code>.", bullet_style))
    story.append(Paragraph("6. <b>Append Audit Log & Commit:</b> Insert into <code>audit_log</code>. Call <code>session.commit()</code>. Invalidate Redis campaign cache and broadcast SSE event to live subscribers.", bullet_style))
    story.append(Paragraph("<i>If any single step fails, the entire transaction rolls back via <code>session.rollback()</code>, ensuring zero partial data corruption.</i>", body_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Workflow 2: Append-Only Audit Log Database Trigger", h2_style))
    story.append(Paragraph(
        "To guarantee that not even a compromised database administrator can alter or delete past records, GiveNaija uses database-level triggers:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>On PostgreSQL:</b> A PL/pgSQL function <code>prevent_audit_log_modifications()</code> raises an EXCEPTION on <code>BEFORE UPDATE OR DELETE</code>. Trigger <code>trg_audit_log_append_only</code> enforces this rule on the table.", bullet_style))
    story.append(Paragraph("&bull; <b>On SQLite (Test Engine):</b> Two <code>BEFORE UPDATE</code> and <code>BEFORE DELETE</code> triggers execute <code>SELECT RAISE(ABORT, 'Audit log is append-only')</code>.", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Workflow 3: Webhook Verification and Orphan Event Handling", h2_style))
    story.append(Paragraph(
        "Payment gateways (Paystack, Flutterwave) notify the system via webhooks. The system executes:",
        body_style
    ))
    story.append(Paragraph("1. <b>HMAC Signature Verification:</b> The raw request body is hashed with the webhook secret using HMAC-SHA256 and compared to the <code>X-Signature</code> header. Mismatches return 401 Unauthorized immediately.", bullet_style))
    story.append(Paragraph("2. <b>Event Idempotency:</b> Check <code>processed_events</code> table for <code>event_id</code>. If already processed, return 200 OK immediately with no side effects.", bullet_style))
    story.append(Paragraph("3. <b>Orphan Handling:</b> If the payment references an unknown or deleted campaign, the system records it in <code>processed_events</code> with <code>is_orphan=True</code> and writes an audit log row, returning 200 OK to the gateway so it stops retrying, while flagging it for manual finance review.", bullet_style))

    story.append(PageBreak()) # Clean page break for Q&A

    # ---------------------------------------------------------
    # PRESENTATION & VIVA PREPARATION
    # ---------------------------------------------------------
    story.append(Paragraph("5. Presentation & Viva Defense: Questions & Answers", h1_style))
    story.append(Paragraph("These are the most probable technical questions examiners and instructors will ask during your capstone defense, along with concise, model answers:", body_style))

    qa_list = [
        (
            "Q1: Why did you enforce append-only audit logs at the database level rather than in your FastAPI Python code?",
            "If audit log restrictions are only written in Python code, anyone with direct SQL access (such as a database administrator, a compromised backend server, or a rogue script) could execute 'DELETE FROM audit_log' or 'UPDATE audit_log'. By writing stored triggers directly in the PostgreSQL engine, the database itself rejects UPDATE and DELETE queries regardless of where the command originates."
        ),
        (
            "Q2: How does your system prevent double-counting when two finance officers submit the same bank reference simultaneously?",
            "We use a two-step defense. First, the 'donations' table has a database-level UNIQUE constraint on 'bank_ref'. When two concurrent requests execute simultaneously, the database's ACID transaction isolation guarantees that only one row can acquire the unique key lock. The second request immediately triggers an IntegrityError, which our service catches and translates into an HTTP 409 Conflict response with a clear error code."
        ),
        (
            "Q3: What is an Idempotency-Key and why is it necessary if you already have bank_ref UNIQUE?",
            "Network timeouts can cause a client to send a request, have the server process it successfully, but disconnect before receiving the HTTP 201 response. The client then retries. The Idempotency-Key header allows the client to retry safely: the server recognizes the key, looks up the cached original response, and returns HTTP 200 with the exact same data without re-executing the donation or throwing an error."
        ),
        (
            "Q4: Why did you use Server-Sent Events (SSE) instead of WebSockets for live campaign donations?",
            "Donation tickers are strictly unidirectional: the server broadcasts updates to frontend dashboards, but clients never need to push data back over the same channel. SSE operates over standard HTTP/1.1 or HTTP/2, requires no special handshake, traverses corporate firewalls effortlessly, supports native automatic reconnection in browsers, and consumes significantly less memory than WebSockets."
        ),
        (
            "Q5: How do you verify that the money in your campaigns matches actual ledger records?",
            "We built the 'GET /ledger/campaign/{id}/verify' endpoint. It queries the immutable 'ledger_entries' table, calculates the exact sum of all CREDIT entries for that campaign, and compares it against the campaign's 'raised_amount'. If the values match, it returns 'match: True' and status 'OK'. If they ever deviate, it flags a reconciliation alert for immediate investigation."
        ),
        (
            "Q6: Why did you configure PostgreSQL Docker to port 5433 instead of the standard 5432?",
            "The host machine had a native Windows PostgreSQL service running locally on port 5432 with different credentials. To avoid port binding collisions and prevent authentication failures, we mapped the Docker container's external port to 5433 while keeping the internal container port on 5432. The application configuration points cleanly to port 5433."
        ),
    ]

    for q, a in qa_list:
        story.append(Paragraph(q, qa_q_style))
        story.append(Paragraph(a, qa_a_style))

    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # DEMO CHEAT SHEET & COMMANDS
    # ---------------------------------------------------------
    story.append(Paragraph("6. Live Demonstration Quick-Reference Sheet", h1_style))
    
    cred_data = [
        [Paragraph("<b>Role</b>", body_style), Paragraph("<b>Email</b>", body_style), Paragraph("<b>Password</b>", body_style), Paragraph("<b>Permissions & Capabilities</b>", body_style)],
        [Paragraph("<b>Admin</b>", body_style), Paragraph("admin@givenaija.org", code_style), Paragraph("Admin123!", code_style), Paragraph("Full system access, view audit logs, create campaigns, reconcile ledger.", body_style)],
        [Paragraph("<b>Finance</b>", body_style), Paragraph("finance@givenaija.org", code_style), Paragraph("Finance123!", code_style), Paragraph("Record manual bank donations, export statements, view campaign ledger.", body_style)],
        [Paragraph("<b>Donor</b>", body_style), Paragraph("donor@givenaija.org", code_style), Paragraph("Donor123!", code_style), Paragraph("Pledge donations, view personal donation history, view own receipts.", body_style)],
    ]
    t_cred = Table(cred_data, colWidths=[70, 160, 100, 210])
    t_cred.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_cred)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Essential Commands for Demonstration:", h2_style))
    story.append(Paragraph("<b>1. Start the Live Server:</b><br/><code>uv run uvicorn app.main:app --reload --port 8000</code>", code_style))
    story.append(Paragraph("<b>2. Run Full Automated Test Suite (31 Tests):</b><br/><code>uv run pytest -v</code>", code_style))
    story.append(Paragraph("<b>3. Simulate Gateway Webhook Payments:</b><br/><code>uv run python mock_payment_provider.py --url http://127.0.0.1:8000/api/v1/webhooks/payment --secret webhook_secret_key_12345 --reference TXN-LIVE-DEMO-001 --amount 5000000 --duplicate</code>", code_style))
    story.append(Paragraph("<b>4. Open Interactive Swagger Documentation:</b><br/><code>http://127.0.0.1:8000/docs</code>", code_style))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Successfully generated {filename}")


if __name__ == "__main__":
    create_pdf()
