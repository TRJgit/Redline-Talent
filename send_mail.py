import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load your .env file
load_dotenv()

def send_outreach_email(receiver_email: str, subject: str, body_html: str, simulate: bool = False) -> str:
    """
    Sends an HTML email or simulates it for testing.
    """
    sender_email = os.getenv("SENDER_EMAIL")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not sender_email or not password:
        return "Error: Email credentials not found. Check your .env file."

    # 1. Structure the Email
    message = MIMEMultipart()
    message["From"] = f"AI Hiring Agent <{sender_email}>"
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body_html, "html"))

    # 2. Simulation Mode (Dry Run)
    if simulate:
        print("\n" + "="*40)
        print(f"🕵️‍♂️ [AGENT TOOL LOG] Simulating Outreach...")
        print(f"To: {receiver_email}")
        print(f"Subject: {subject}")
        print("="*40 + "\n")
        return f"Success: Email successfully simulated to {receiver_email}."

    # 3. Live Execution with Try/Except Block
    try:
        # Connect to Gmail's SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            # THIS LINE HELPS US DEBUG
            server.set_debuglevel(1) 
            
            server.ehlo() # Identify ourselves to the smtp server
            server.starttls() # Secure the connection
            server.ehlo() # Re-identify as an encrypted connection
            
            # Attempt to log in
            server.login(sender_email, password)
            
            # Send the email
            server.sendmail(sender_email, receiver_email, message.as_string())
            
        print("Email sent successfully!")
        return f"Success: Live email sent to {receiver_email}."
        
    except smtplib.SMTPAuthenticationError:
        error_msg = "Error: Authentication failed. Your App Password or Email in the .env file is incorrect."
        print(error_msg)
        return error_msg
        
    except smtplib.SMTPConnectError:
        error_msg = "Error: Failed to connect to the Gmail server. Check your internet connection."
        print(error_msg)
        return error_msg
        
    except Exception as e:
        # Catch-all for any other unexpected errors
        error_msg = f"Error: An unexpected error occurred: {str(e)}"
        print(error_msg)
        return error_msg

# ==========================================
# Example usage to test your setup:
# ==========================================
if __name__ == "__main__":
    # Ensure this is the email you want to send TO
    test_receiver = "your.personal.email@gmail.com" 
    test_subject = "Hackathon Test: You're Hired!"
    test_body = """
    <html>
        <body>
            <h2>Hello!</h2>
            <p>This is a test from the AI Hiring Agent.</p>
        </body>
    </html>
    """
    
    # Run a live test
    result = send_outreach_email(test_receiver, test_subject, test_body, simulate=False)
    print(f"Agent feedback: {result}")