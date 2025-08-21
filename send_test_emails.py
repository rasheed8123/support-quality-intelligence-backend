#!/usr/bin/env python3
"""
Send Test Emails for Comprehensive Testing
Sends all test scenarios to verify Gmail webhook and RAG pipeline.
"""

import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-test-email@gmail.com"  # Replace with your Gmail
SENDER_PASSWORD = "your-app-password"       # Replace with your Gmail app password
SUPPORT_EMAIL = "support@yourcompany.com"   # Replace with your support email

def send_email(from_email, to_email, subject, body, reply_to_message_id=None):
    """Send an email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if reply_to_message_id:
            msg['In-Reply-To'] = reply_to_message_id
            msg['References'] = reply_to_message_id
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        
        print(f"✅ Email sent: {subject}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def main():
    """Send all test emails"""
    print("🚀 SENDING COMPREHENSIVE TEST EMAILS")
    print("="*60)
    
    # THREAD 1: SPAM DETECTION
    print("\n📧 THREAD 1: SPAM DETECTION")
    send_email(
        "marketing@deals4u.com",
        SUPPORT_EMAIL,
        "🎉 AMAZING DEAL! 90% OFF Everything - Limited Time!",
        """Dear Customer,

This is your LAST CHANCE to get 90% OFF on all our amazing products! 

🔥 EXCLUSIVE OFFERS:
- Bitcoin investment opportunities
- Make $10,000 in 24 hours
- Click here to claim your prize

Don't miss out! Act NOW before this offer expires!

Best regards,
Marketing Team"""
    )
    
    time.sleep(5)  # Wait between emails
    
    # THREAD 2: HIGH PRIORITY QUERY THREAD
    print("\n📧 THREAD 2: HIGH PRIORITY QUERY THREAD")
    
    # Email 1
    send_email(
        "frustrated.student@gmail.com",
        SUPPORT_EMAIL,
        "Course enrollment question",
        """Hi,

I'm interested in your Data Science course. Could you please provide details about the fee, duration, and enrollment process?

Thanks,
Sarah Johnson"""
    )
    
    time.sleep(10)
    
    # Email 2 (Support Response)
    send_email(
        SUPPORT_EMAIL,
        "frustrated.student@gmail.com",
        "Re: Course enrollment question",
        """Hi Sarah,

Thank you for your interest in our Data Science course!

Here are the details:
- Course fee: ₹50,000
- Duration: 6 months
- Enrollment: Online application with immediate access after payment

Please let me know if you have any other questions.

Best regards,
Support Team"""
    )
    
    time.sleep(10)
    
    # Email 3 (High Priority Issue)
    send_email(
        "frustrated.student@gmail.com",
        SUPPORT_EMAIL,
        "URGENT: Cannot access course after payment",
        """Hi,

I paid ₹50,000 yesterday but still cannot access the Data Science course. This is very frustrating as I need to start immediately for my job interview preparation. Please resolve this ASAP!

I have the payment confirmation: Transaction ID TXN123456789

Sarah Johnson"""
    )
    
    time.sleep(15)
    
    # THREAD 3: MEDIUM PRIORITY QUERY THREAD
    print("\n📧 THREAD 3: MEDIUM PRIORITY QUERY THREAD")
    
    send_email(
        "curious.learner@yahoo.com",
        SUPPORT_EMAIL,
        "Certificate validity and instructor details",
        """Hello,

I wanted to clarify a few things about the Python programming course:

1. Is the certificate industry recognized?
2. What is the validity period of the certificate?
3. Could you provide details about the instructor's experience?
4. What are the batch timings for the next session?

Looking forward to your response.

Best regards,
Alex Kumar"""
    )
    
    time.sleep(10)
    
    send_email(
        SUPPORT_EMAIL,
        "curious.learner@yahoo.com",
        "Re: Certificate validity and instructor details",
        """Hi Alex,

Thank you for your questions about the Python course:

1. Yes, our certificate is industry recognized by over 500 companies
2. The certificate has lifetime validity
3. Our instructor has 15+ years of experience in Python and machine learning
4. Next batch starts on Monday, Wednesday, Friday from 7-9 PM IST

The course fee is approximately ₹35,000-40,000 (exact amount depends on current offers).

Best regards,
Support Team"""
    )
    
    time.sleep(15)
    
    # THREAD 4: LOW PRIORITY QUERY THREAD
    print("\n📧 THREAD 4: LOW PRIORITY QUERY THREAD")
    
    send_email(
        "grateful.student@outlook.com",
        SUPPORT_EMAIL,
        "Thank you for the excellent course",
        """Dear Team,

I just completed the Data Science course and wanted to express my gratitude. The content was excellent, the instructor was very helpful, and the practical projects were really valuable.

I would highly recommend this course to anyone looking to upskill in data science.

Thank you once again!

Best regards,
Priya Sharma"""
    )
    
    time.sleep(10)
    
    send_email(
        SUPPORT_EMAIL,
        "grateful.student@outlook.com",
        "Re: Thank you for the excellent course",
        """Dear Priya,

Thank you so much for your wonderful feedback! We're thrilled to hear that you had such a positive experience with our Data Science course.

Your success is our motivation, and we're glad the practical projects were valuable for your learning journey.

We'd love to have you back for our advanced courses. Keep an eye out for our upcoming Machine Learning specialization!

Best regards,
Support Team"""
    )
    
    print(f"\n🎉 ALL TEST EMAILS SENT SUCCESSFULLY!")
    print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 NEXT STEPS:")
    print("1. Wait 5-10 minutes for all emails to be processed")
    print("2. Check your database for email records")
    print("3. Verify RAG pipeline results")
    print("4. Check alert system for any triggered alerts")
    print("5. Review logs for any processing errors")

if __name__ == "__main__":
    print("⚠️  IMPORTANT: Update email configuration before running!")
    print("   - Set SENDER_EMAIL to your Gmail address")
    print("   - Set SENDER_PASSWORD to your Gmail app password")
    print("   - Set SUPPORT_EMAIL to your support email address")
    print()
    
    confirm = input("Have you updated the email configuration? (yes/no): ").strip().lower()
    if confirm in ['yes', 'y']:
        main()
    else:
        print("❌ Please update the configuration and run again.")
