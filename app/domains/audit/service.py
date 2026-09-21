import logging
from typing import Optional
from sqlalchemy import text
from sqlmodel import Session, select, func

from app.domains.audit.models import AuditLog
from app.domains.audit.schemas import AuditLogListResponse, AuditLogResponse

logger = logging.getLogger(__name__)


class AuditService:
    """
    Audit Trail management and database-level immutability enforcement.
    """

    @staticmethod
    def list_logs(
        session: Session,
        actor_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> AuditLogListResponse:
        query = select(AuditLog)
        if actor_id is not None:
            query = query.where(AuditLog.actor_id == actor_id)

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        logs = session.exec(
            query.offset(offset).limit(limit).order_by(AuditLog.at.desc())
        ).all()

        items = [AuditLogResponse.model_validate(l) for l in logs]
        return AuditLogListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def enforce_append_only_rules(engine) -> None:
        """
        Installs triggers in the database engine to guarantee that
        UPDATE and DELETE statements on audit_log fail at the database level.
        """
        dialect = engine.dialect.name.lower()

        if dialect == "postgresql":
            sql = """
            CREATE OR REPLACE FUNCTION prevent_audit_log_modifications()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE operations are strictly prohibited.';
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_audit_log_append_only ON audit_log;
            CREATE TRIGGER trg_audit_log_append_only
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_modifications();
            """
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            logger.info("PostgreSQL append-only trigger activated on audit_log.")

        elif dialect == "sqlite":
            sql_update = """
            CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log is append-only: UPDATE is prohibited');
            END;
            """
            sql_delete = """
            CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log is append-only: DELETE is prohibited');
            END;
            """
            with engine.connect() as conn:
                conn.execute(text(sql_update))
                conn.execute(text(sql_delete))
                conn.commit()
            logger.info("SQLite append-only triggers activated on audit_log.")
