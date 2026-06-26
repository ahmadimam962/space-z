"""
Auth Data Cleanup Module
-------------------------
This module handles periodic cleanup of expired authentication data
to prevent database bloat and maintain security.

Cleanup targets:
1. Expired OTP codes (past their expires_at timestamp)
2. Old pending registrations (older than 30 minutes)

This module is called by a scheduled background job (see main.py).
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import OTPCode, PendingRegistration


def cleanup_expired_auth_data(db: Session) -> None:
    """
    Remove expired OTP codes and stale pending registrations from the database.
    
    This function performs two cleanup operations:
    1. Deletes all OTP codes where expires_at < current time
    2. Deletes all pending registrations created more than 30 minutes ago
    
    Args:
        db (Session): An active SQLAlchemy database session.
        
    Note:
        This function commits the transaction. The caller should handle
        session lifecycle (open/close).
    """
    now = datetime.utcnow()
    
    # 1. Delete expired OTP codes
    db.query(OTPCode).filter(
        OTPCode.expires_at < now
    ).delete()
    
    # 2. Delete pending registrations older than 30 minutes
    # (users who didn't complete email verification in time)
    old_pending_time = now - timedelta(minutes=30)
    
    db.query(PendingRegistration).filter(
        PendingRegistration.created_at < old_pending_time
    ).delete()
    
    # Commit both deletions in a single transaction
    db.commit()