"""
Email Service Module
---------------------
This module handles sending transactional emails via SMTP.
Currently supports:
- OTP verification emails (registration, password reset)

Uses Python's built-in smtplib and email.mime modules.
Configuration is loaded from app.config.settings.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


def send_otp_email(to_email: str, otp_code: str) -> None:
    """
    Send an OTP verification email to the specified recipient.
    
    The email contains a verification code that expires in 10 minutes.
    Uses HTML format for better presentation.
    
    Args:
        to_email (str): The recipient's email address.
        otp_code (str): The OTP code to include in the email.
        
    Raises:
        smtplib.SMTPException: If there's an error connecting to the SMTP server
            or sending the email. The caller should handle this appropriately.
            
    Note:
        This function uses STARTTLS for secure email transmission.
        SMTP credentials are loaded from environment variables via settings.
    """
    # 1. Create the email message with HTML content
    message = MIMEMultipart("alternative")
    message["Subject"] = "Space Z Verification Code"
    message["From"] = settings.EMAIL_USER
    message["To"] = to_email
    
    # 2. Build the HTML body
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Space Z</h2>
            <p>Your verification code is:</p>
            <h1 style="color: #4A90E2; letter-spacing: 5px;">{otp_code}</h1>
            <p style="color: #666;">This code expires in 10 minutes.</p>
        </body>
    </html>
    """
    
    message.attach(MIMEText(html, "html"))
    
    # 3. Connect to SMTP server and send the email
    # Using 'with' statement ensures the connection is properly closed
    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        server.starttls()  # Upgrade to secure connection
        server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
        server.sendmail(settings.EMAIL_USER, to_email, message.as_string())