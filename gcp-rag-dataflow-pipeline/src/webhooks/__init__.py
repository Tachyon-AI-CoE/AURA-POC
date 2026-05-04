"""Webhooks package for RAG pipeline notifications."""

from .webhook_notifier import send_rag_status

__all__ = ['send_rag_status']
