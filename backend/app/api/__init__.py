"""
API routes package
"""

from app.api import health, evaluations, analytics, settings, scan

__all__ = ["health", "evaluations", "analytics", "settings", "scan"]
