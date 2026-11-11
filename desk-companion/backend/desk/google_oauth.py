"""Compatibility name for the existing read-only Calendar connector."""

from .app_oauth import AppOAuth as GoogleOAuth
from .app_specs import SCOPES, CALLBACKS

__all__ = ["GoogleOAuth", "SCOPES", "CALLBACKS"]
