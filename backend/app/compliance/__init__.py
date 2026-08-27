"""Versioned legal-document and consent enforcement boundary."""

from app.compliance.documents import current_legal_documents
from app.compliance.service import require_current_legal_acceptance

__all__ = ("current_legal_documents", "require_current_legal_acceptance")
