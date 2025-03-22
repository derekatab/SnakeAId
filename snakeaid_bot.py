from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    print("Warning: Twilio credentials not found. Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.")
else:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Backend API configuration
BACKEND_URL = 'http://localhost:5001/api'

#  conversation flow
user_sessions = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.form.get("Body", "").lower()
    sender = request.form.get("From")
    response = MessagingResponse()
    msg = response.message()

    if sender not in user_sessions:
        user_sessions[sender] = {"step": 0, "description": {}, "symptoms": []}

    session = user_sessions[sender]

    if session["step"] == 0:
        msg.body("Hello! I can help you identify snakes and provide first aid information. Would you like to:\n1. Describe a snake's appearance\n2. List symptoms from a snake bite\n3. Send a photo of a snake")
        session["step"] = 1
        return str(response)

    if session["step"] == 1:
        if "1" in incoming_msg:
            msg.body("Please describe the snake's color and any distinctive patterns:")
            session["step"] = 2
        elif "2" in incoming_msg:
            msg.body("Please list the symptoms you're experiencing (separated by commas):")
            session["step"] = 3
        elif "3" in incoming_msg:
            msg.body("Please send a photo of the snake.")
            session["step"] = 4
        else:
            msg.body("Please choose 1, 2, or 3")
        return str(response)

    if session["step"] == 2:
        # Search snakes by description
        search_response = requests.get(f"{BACKEND_URL}/snakes/search", params={"q": incoming_msg})
        if search_response.status_code == 200:
            snakes = search_response.json()
            if snakes:
                response_text = "Possible matches:\n\n"
                for snake in snakes[:3]:  # Limit to top 3 matches
                    response_text += f"Name: {snake['name']}\n"
                    response_text += f"Color: {snake['color']}\n"
                    response_text += f"Venom: {snake['venom']}\n"
                    response_text += f"First Aid: {snake['first_aid']}\n\n"
            else:
                response_text = "No snakes found matching that description. Please try again with different details."
        else:
            response_text = "Sorry, there was an error processing your request."
        
        msg.body(response_text)
        session["step"] = 0
        return str(response)

    if session["step"] == 3:
        # Search by symptoms
        symptoms = [s.strip() for s in incoming_msg.split(",")]
        search_response = requests.get(f"{BACKEND_URL}/symptoms/search", params={"symptoms": symptoms})
        
        if search_response.status_code == 200:
            snakes = search_response.json()
            if snakes:
                response_text = "Based on the symptoms, possible snake matches:\n\n"
                for snake in snakes[:3]:
                    response_text += f"Name: {snake['name']}\n"
                    response_text += f"Venom: {snake['venom']}\n"
                    response_text += f"First Aid: {snake['first_aid']}\n\n"
            else:
                response_text = "No specific matches found. Please seek immediate medical attention if you've been bitten by a snake."
        else:
            response_text = "Sorry, there was an error processing your request."
            
        msg.body(response_text)
        session["step"] = 0
        return str(response)

    if session["step"] == 4:
        if request.values.get('NumMedia', 0) != "0":
            # Get the image URL from the message
            image_url = request.values.get('MediaUrl0')
            
            # Download the image
            image_response = requests.get(image_url)
            
            # Send to backend API for analysis
            files = {'image': ('snake.jpg', image_response.content)}
            analysis_response = requests.post(f"{BACKEND_URL}/snakes/analyze", files=files)
            
            if analysis_response.status_code == 200:
                result = analysis_response.json()
                if 'details' in result:
                    snake = result['details']
                    response_text = f"Snake identified as: {snake['name']}\n"
                    response_text += f"Scientific name: {snake['scientific_name']}\n"
                    response_text += f"Venom type: {snake['venom']}\n"
                    response_text += f"First Aid:\n{snake['first_aid']}"
                else:
                    response_text = result.get('warning', 'Unable to identify the snake.')
            else:
                response_text = "Sorry, there was an error analyzing the image."
        else:
            response_text = "No image received. Please send a photo of the snake."
            
        msg.body(response_text)
        session["step"] = 0
        return str(response)

    msg.body("Sorry, I didn't understand that. Let's start over.")
    session["step"] = 0
    return str(response)

if __name__ == "__main__":
    app.run(port=5000, debug=True)