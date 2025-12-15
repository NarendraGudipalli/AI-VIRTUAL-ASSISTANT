from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from app.models import UserProfile, ChatRequest, ChatResponse, LoginRequest, VerifyRequest
from app.engine import WellnessEngine
from app.nlp import analyze_input
import random
import os
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="NARI.ai Wellness Assistant")

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

engine = WellnessEngine()
user_profile = UserProfile() # Simple in-memory profile for now
otp_storage = {} # Store OTPs temporarily: {contact: otp}

def send_real_sms(to_number, otp):
    try:
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        from_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, from_number]):
            return False, "Twilio credentials missing"

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Your Wellness Assistant OTP is: {otp}",
            from_=from_number,
            to=to_number
        )
        print(f"SMS sent: {message.sid}")
        return True, "SMS sent"
    except Exception as e:
        print(f"Twilio Error: {e}")
        return False, str(e)

def send_real_email(to_email, otp):
    try:
        sender_email = os.getenv('EMAIL_SENDER')
        password = os.getenv('EMAIL_PASSWORD')
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        
        if not all([sender_email, password, smtp_server]):
            return False, "Email credentials missing"

        msg = MIMEText(f"Your Wellness Assistant OTP is: {otp}")
        msg['Subject'] = "Your Login OTP"
        msg['From'] = sender_email
        msg['To'] = to_email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        return True, "Email sent"
    except Exception as e:
        print(f"Email Error: {e}")
        return False, str(e)

@app.get("/")
async def root():
    return {"message": "Welcome to AI Virtual Assistant API"}

@app.post("/api/login")
async def login(request: LoginRequest):
    """
    Generate and send OTP (Real if keys exist, else Mock).
    """
    otp = str(random.randint(100000, 999999))
    otp_storage[request.contact] = otp
    
    delivery_status = "simulated"
    error_msg = ""
    
    # Check if contact is email or phone
    if "@" in request.contact:
        success, msg = send_real_email(request.contact, otp)
        if success:
            delivery_status = "email_sent"
        else:
            error_msg = msg
    else:
        # Assume phone
        success, msg = send_real_sms(request.contact, otp)
        if success:
            delivery_status = "sms_sent"
        else:
            error_msg = msg

    print(f"MODULE: OTP for {request.contact} is {otp} (Status: {delivery_status})") 
    
    # Always returning otp in debug_otp for fallback/demo purposes
    return {
        "message": f"OTP sent ({delivery_status})", 
        "debug_otp": otp, 
        "delivery_status": delivery_status,
        "error": error_msg
    } 

@app.post("/api/verify")
async def verify(request: VerifyRequest):
    """
    Verify the OTP.
    """
    if request.contact in otp_storage and otp_storage[request.contact] == request.otp:
        del otp_storage[request.contact]
        return {"message": "Login successful", "token": "mock-jwt-token"}
    raise HTTPException(status_code=400, detail="Invalid OTP")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle user chat input.
    """
    user_input = request.message
    
    # 1. Analyze Input
    intent, entities = analyze_input(user_input)
    
    # 2. Update Profile if needed (Mock logic)
    if intent == "update_profile":
        # Simple update based on entities found
        if "name" in entities:
            user_profile.name = entities["name"]
        if "age" in entities:
            user_profile.age = int(entities["age"])
            
    # 3. Generate Response via Engine
    response_text = engine.generate_response(intent, entities, user_profile)
    
    return ChatResponse(message=response_text)

@app.get("/api/profile")
async def get_profile():
    return user_profile

@app.post("/api/profile")
async def update_profile(profile: UserProfile):
    global user_profile
    user_profile = profile
    return {"message": "Profile updated", "profile": user_profile}
