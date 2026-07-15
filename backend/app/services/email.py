import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(receiver_email: str, otp: str) -> bool:
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_email or not smtp_password:
        print(f"WARNING: SMTP_EMAIL or SMTP_PASSWORD is not configured. Skipped sending OTP email to {receiver_email}. OTP Code: {otp}")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = receiver_email
        msg['Subject'] = "Your Mock Interview Platform Password Reset OTP"
        
        body = (
            f"Hello,\n\n"
            f"You requested to reset your password on the AI Smart Interview Analyzer Platform.\n\n"
            f"Please use the following One-Time Password (OTP) code:\n\n"
            f"OTP Code: {otp}\n\n"
            f"This code will expire in 5 minutes.\n\n"
            f"If you did not request a password reset, please ignore this email.\n\n"
            f"Best regards,\n"
            f"AI Mock Interview Prep Team"
        )
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, receiver_email, msg.as_string())
        server.quit()
        print(f"OTP Email dispatched successfully to {receiver_email}!")
        return True
    except Exception as e:
        print(f"Failed to dispatch OTP email to {receiver_email}: {e}")
        return False
