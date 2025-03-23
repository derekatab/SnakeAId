import os
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import traceback
from flask_cors import CORS
import random

# Load environment variables from .env file
# Use absolute path to ensure correct loading
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# Debugging environment variable loading
print("Current Working Directory:", os.getcwd())
print("Environment File Path:", env_path)
print("Environment File Exists:", os.path.exists(env_path))

# Print all environment variables for debugging
print("\nAll Environment Variables:")
for key, value in os.environ.items():
    print(f"{key}: {'*' * len(value) if 'KEY' in key or 'TOKEN' in key else value}")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    print("Warning: Twilio credentials not found. Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.")
else:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Gemini API configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyC91lYMZjNiUw_AuzzniWHqDqWVeH0De9Q')
print(f"Gemini API Key (first 5 chars): {GEMINI_API_KEY[:5]}...")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# List available models and their details
try:
    models = genai.list_models()
    print("\nAvailable Gemini Models:")
    for m in models:
        print(f"- {m.name}: {m.description}")
except Exception as list_error:
    print(f"\nError listing models: {list_error}")

# Create Gemini model
try:
    # Use the latest stable Flash model
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    # Perform a quick test generation to validate model
    test_response = model.generate_content("Generate a short emergency first aid message.")
    print("Gemini model successfully initialized.")
    print("Test response:", test_response.text)
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    model = None

# Global variable to track conversation state and asked questions
conversation_state = {}

# WHO First Aid Guidelines Context - ONLY knowledge the bot has
who_guidelines = """
WHO Snake Bite First Aid Guidelines:
- Keep the person calm and still - many snake bites are non-venomous and even venomous bites aren't immediately fatal
- Remove anything tight from around the bitten part (rings, anklets, bracelets) as these can cause harm if swelling occurs
- Immobilize the person completely and splint the limb
- Monitor airway and breathing, be ready to resuscitate if needed
- Transport to health facility ASAP
- If vomiting occurs, place person on left side
- Use a makeshift stretcher to carry the person to transport
- Never use a tight arterial tourniquet
- Australian Pressure Immobilization Bandage only for neurotoxic snakes without local swelling
- Applying pressure at bite site with pressure pad may be suitable in some cases
- Avoid traditional first aid methods and herbal medicines
- Paracetamol may be given for local pain
- If snake is still attached use a stick or tool to make it let go
- Sea snake victims need to be moved to dry land to avoid drowning
- Ensure area is safe before providing care
"""

# Makeshift Stretcher Methods Context - ONLY knowledge about stretchers
stretcher_methods = """
Makeshift Stretcher Methods:
1. Rope Stretcher:
   - Lay zigzag rope pattern larger than victim
   - Secure ends with clove hitches
   - Thread poles through loops for stability

2. Tarp Stretcher:
   - Lay tarp flat
   - Position poles in folding pattern
   - Fold sections over poles
   - Use victim's weight to hold tarp

3. Duct Tape Stretcher:
   - Create 4 perpendicular duct tape straps
   - Add long center support strap
   - Reinforce with diagonal straps

4. Jacket Stretcher:
   - Invert 2-3 jacket sleeves
   - Thread poles through sleeves
   - Secure with diagonal lashings
"""

# Predefined initial message variations
initial_message_variations = [
    """Move them away from the snake. Remove any tight items like rings or bracelets. Keep them calm and still.
Keep their leg still and straight. Don't tie anything around it or try to cut or suck the bite.
If transport is far, make a stretcher using a tarp, rope, or jackets. Get them to a health facility ASAP.
If they feel dizzy or vomit, lay them on their left side. Watch their breathing and be ready to help if needed.""",
    
    """First, ensure they're away from the snake. Take off any tight jewelry or clothing near the bite.
Keep them as still as possible, with the affected limb straight and immobilized.
If you need to transport them, create a stretcher from available materials and get to medical help quickly.
If they start feeling dizzy or vomiting, position them on their left side and monitor their breathing.""",
    
    """Get them to a safe distance from the snake first. Remove any constricting items like rings or bracelets.
Keep them calm and completely still, with the bitten limb straight and supported.
For transport, you can make a stretcher from a tarp, rope, or jackets if needed. Head to medical care right away.
Watch for dizziness or vomiting - if these occur, lay them on their left side and keep monitoring their breathing.""",
    
    """Start by moving them away from the snake's location. Take off any tight items near the bite area.
Help them stay calm and motionless, keeping the affected limb straight and still.
If you need to carry them, create a stretcher from available materials and get to medical help immediately.
If they become dizzy or vomit, place them on their left side and watch their breathing carefully.""",
    
    """First priority: get them away from the snake. Remove any tight jewelry or clothing from the bite area.
Keep them completely still and calm, with the bitten limb straight and supported.
For longer distances, make a stretcher from tarp, rope, or jackets. Get to medical help as soon as possible.
If they feel dizzy or vomit, position them on their left side and monitor their breathing closely."""
]

# Predefined questions and responses
predefined_questions = [
    "Have you removed any tight items like rings or bracelets from around the bite area?",
    "Is the person calm and still?",
    "How is their breathing? Are they conscious and alert?",
    "Has the affected limb been immobilized?",
    "Do you need help preparing transport to a medical facility?",
    "Is the person showing any signs of dizziness or vomiting?",
    "Do you have materials available to make a stretcher if needed?",
    "Can you tell me about their current condition?",
    "Is the person able to speak and respond to questions?",
    "Do you have access to medical help nearby?"
]

predefined_responses = {
    'positive': [
        "That's good. Let's continue monitoring their condition.",
        "Keep up the good care. Let's check something else.",
        "Well done. Let's make sure we haven't missed anything.",
        "That's helpful information. Let's check another aspect.",
        "Good to hear. Let's verify another important detail."
    ],
    'negative': [
        "Let's address that right away.",
        "We should focus on that now.",
        "That's important to handle immediately.",
        "Let's work on that together.",
        "We need to take care of that."
    ],
    'needs_help': [
        "I'll help you with that.",
        "Let me guide you through this.",
        "I can help you with that step.",
        "Let's work on this together.",
        "I'll walk you through this."
    ]
}

def get_predefined_response(message, current_state):
    """Generate a response using predefined questions and responses."""
    try:
        # Initialize state if needed
        if 'asked_questions' not in current_state:
            current_state['asked_questions'] = set()
            current_state['completed_actions'] = set()
        
        # Get the last question asked
        last_question = current_state.get('last_question', '')
        
        # Evaluate the user's response
        message_lower = message.lower()
        is_affirmative = any(word in message_lower for word in ['yes', 'yeah', 'done', 'okay', 'ok', 'sure', 'ready'])
        is_negative = any(word in message_lower for word in ['no', 'not', 'haven\'t', 'can\'t', 'cannot', 'didn\'t'])
        needs_help = any(word in message_lower for word in ['help', 'how', 'what', 'unclear', 'explain', 'don\'t understand'])
        
        # Generate response based on user's answer
        if is_affirmative:
            response = random.choice(predefined_responses['positive'])
        elif is_negative:
            response = random.choice(predefined_responses['negative'])
        elif needs_help:
            response = random.choice(predefined_responses['needs_help'])
        else:
            response = "Let's check something else."
        
        # Get next question
        available_questions = [q for q in predefined_questions if q not in current_state['asked_questions']]
        if not available_questions:
            available_questions = predefined_questions
        next_question = random.choice(available_questions)
        
        # Update state
        current_state['asked_questions'].add(next_question)
        current_state['last_question'] = next_question
        
        return f"{response}\n\n{next_question}"
        
    except Exception as e:
        return "How is the person's condition now?"

def generate_response(message, sender=None):
    """Generate a conversational response based strictly on guidelines."""
    try:
        # Initialize or get conversation state
        if sender not in conversation_state:
            conversation_state[sender] = {
                'is_initial': True,
                'asked_questions': set(),
                'completed_actions': set(),
                'moved_from_snake': False,
                'removed_tight_items': False,
                'checked_breathing': False,
                'in_recovery_position': False,
                'stretcher_step': 0,
                'has_shown_initial_message': False
            }
        
        current_state = conversation_state[sender]
        
        # Check if this is the first user message and we haven't shown the initial message yet
        is_first_message = request.json.get('is_first_message', False)
        
        if is_first_message and not current_state.get('has_shown_initial_message', False):
            # Use predefined initial message
            initial_response = random.choice(initial_message_variations)
            
            # Get first follow-up question
            first_question = random.choice(predefined_questions)
            current_state['asked_questions'].add(first_question)
            current_state['last_question'] = first_question
            current_state['has_shown_initial_message'] = True
            
            return f"{initial_response}\n\n{first_question}"
        
        # For subsequent messages, use predefined responses
        return get_predefined_response(message, current_state)
            
    except Exception as e:
        return "Keep monitoring the person's condition. Seek medical help as soon as possible."

# Twilio Stuff to send messages
@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    try:
        # Verify Twilio credentials
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            response = MessagingResponse()
            response.message("Service temporarily unavailable. Please try again later.")
            return str(response)

        # Get incoming message
        incoming_msg = request.form.get("Body", "").strip()
        sender = request.form.get("From", "")
        
        if not incoming_msg or not sender:
            response = MessagingResponse()
            response.message("Invalid request")
            return str(response)

        # Generate response using Gemini
        response_text = generate_response(incoming_msg, sender)
        
        try:
            # Send response using Twilio client
            message = client.messages.create(
                body=response_text,
                from_='whatsapp:+14155238886',  # Twilio's WhatsApp sandbox number
                to=sender
            )
        except Exception as e:
            # Fall back to TwiML response
            response = MessagingResponse()
            response.message(response_text)
            return str(response)
        
        # Return empty TwiML response since we already sent the message
        return str(MessagingResponse())
        
    except Exception as e:
        response = MessagingResponse()
        response.message("An error occurred. Please try again.")
        return str(response)

@app.route("/sms", methods=['POST'])
def sms_reply():
    incoming_msg = request.json.get('Body', '').strip()
    sender = request.json.get('From', 'web-user')
    response_text = generate_response(incoming_msg)
    return response_text

@app.route("/reset", methods=['POST'])
def reset_conversation():
    """Reset the conversation state for the web user."""
    try:
        # Clear the conversation state for web-user
        if 'web-user' in conversation_state:
            del conversation_state['web-user']
        return jsonify({"status": "success", "message": "Conversation reset successfully"}), 200
    except Exception as e:
        print(f"Error resetting conversation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000)