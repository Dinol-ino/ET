from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.contact import Contact


class ContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_external_id(self, external_id: str) -> Contact | None:
        if not external_id:
            return None
        stmt = select(Contact).where(Contact.external_id == external_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Contact | None:
        stmt = select(Contact).where(Contact.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert_contact(self, payload: dict[str, object]) -> Contact:
        external_id = str(payload.get("external_id") or "").strip() or None
        email = str(payload.get("email") or "").strip().lower()
        if not email:
            raise ValueError("Contact email is required")

        contact = None
        if external_id:
            contact = self.get_by_external_id(external_id)
        if contact is None:
            contact = self.get_by_email(email)

        if contact is None:
            contact = Contact(email=email)
            self.db.add(contact)

        contact.external_id = external_id
        contact.email = email
        contact.first_name = self._as_optional_text(payload.get("first_name"))
        contact.last_name = self._as_optional_text(payload.get("last_name"))
        contact.company_name = self._as_optional_text(payload.get("company_name"))
        contact.domain = self._as_optional_text(payload.get("domain"))
        contact.job_title = self._as_optional_text(payload.get("job_title"))

        self.db.flush()
        return contact

    def list_contacts(self, limit: int = 100, offset: int = 0) -> list[Contact]:
        stmt = select(Contact).order_by(Contact.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        stmt = select(func.count(Contact.id))
        return int(self.db.execute(stmt).scalar_one())

    @staticmethod
    def _as_optional_text(value: object) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None
