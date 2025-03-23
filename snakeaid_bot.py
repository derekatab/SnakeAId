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

def evaluate_response(message, current_context):
    """Evaluate user's response to determine next steps."""
    message_lower = message.lower()
    
    # More comprehensive response detection
    is_affirmative = any(word in message_lower for word in [
        'yes', 'yeah', 'done', 'okay', 'ok', 'sure', 'ready', 'moved', 'away', 'safe', 'clear'
    ])
    is_negative = any(word in message_lower for word in [
        'no', 'not', 'haven\'t', 'can\'t', 'cannot', 'didn\'t', 'unable'
    ])
    needs_help = any(word in message_lower for word in [
        'help', 'how', 'what', 'unclear', 'explain', 'don\'t understand', 'confused'
    ])

    # Update context based on response content
    if any(phrase in message_lower for phrase in [
        'moved away', 'away from', 'safe now', 'in safe', 'moved', 'safe place', 
        'away from snake', 'clear of snake', 'different location'
    ]):
        current_context['moved_from_snake'] = True
        current_context['completed_actions'].add('moved_from_snake')
    
    # Update context based on response
    if 'last_question' in current_context:
        last_question = current_context['last_question'].lower()
        
        if ('snake' in last_question or 'moved' in last_question or 'away' in last_question) and is_affirmative:
            current_context['moved_from_snake'] = True
            current_context['completed_actions'].add('moved_from_snake')
        elif 'tight' in last_question or 'ring' in last_question or 'bracelet' in last_question:
            if is_affirmative or 'removed' in message_lower:
                current_context['removed_tight_items'] = True
                current_context['completed_actions'].add('removed_tight_items')
        elif 'breath' in last_question:
            if is_affirmative or any(word in message_lower for word in ['normal', 'fine', 'good', 'breathing']):
                current_context['checked_breathing'] = True
                current_context['completed_actions'].add('checked_breathing')
        elif 'left side' in last_question:
            if is_affirmative or 'positioned' in message_lower:
                current_context['in_recovery_position'] = True
                current_context['completed_actions'].add('in_recovery_position')
    
    return is_affirmative, is_negative, needs_help

def generate_follow_up_question(message, current_context):
    """Generate a contextual follow-up question using Gemini."""
    try:
        # Initialize context if needed
        if 'asked_questions' not in current_context:
            current_context['asked_questions'] = set()
            current_context['completed_actions'] = set()
        
        # Special handling for the first question - use random selection from predefined questions
        first_questions = [
            "Have you removed any tight items like rings or bracelets from around the bite area?",
            "How is their breathing? Are they conscious and alert?",
            "Is the person calm and still?",
            "Can you tell me about their current condition?",
            "Has the affected limb been immobilized?",
            "Do you need help preparing transport to a medical facility?"
        ]
        
        # If it's the first question or if we need a fallback
        if current_context.get('is_first_question', False) or not current_context.get('asked_questions'):
            current_context['is_first_question'] = False
            available_questions = [q for q in first_questions if q not in current_context['asked_questions']]
            if not available_questions:  # If all predefined questions have been asked
                available_questions = first_questions
            selected_question = random.choice(available_questions)
            current_context['asked_questions'].add(selected_question)
            current_context['last_question'] = selected_question
            return selected_question
        
        # For subsequent questions, use Gemini
        context_prompt = f"""Based ONLY on these snake bite first aid guidelines and stretcher methods, generate ONE follow-up question:

WHO Guidelines:
{who_guidelines}

Stretcher Methods:
{stretcher_methods}

Current conversation state:
- User's last message: {message}
- Previously asked questions: {', '.join(current_context['asked_questions'])}
- Completed actions: {', '.join(current_context.get('completed_actions', set()))}
- Last question asked: {current_context.get('last_question', 'None')}

RULES for generating the next question:
1. Focus on patient care in this order:
   - Breathing and consciousness
   - Removing tight items
   - Immobilization
   - Transport preparation
2. Never repeat any previously asked questions
3. Keep questions short and focused
4. Only use information from the guidelines
5. Make questions conversational and natural
6. DO NOT ask about moving away from the snake or snake location

Generate one clear, contextual question that has NOT been asked before:"""

        # Generate question using Gemini
        response = model.generate_content(context_prompt)
        new_question = response.text.strip()
        
        # Clean up and format the question
        new_question = new_question.replace('Question:', '').replace('Next question:', '').strip()
        if not new_question.endswith('?'):
            new_question += '?'
        
        # If the question is about snake location or we got an invalid response, use random selection
        if any(word in new_question.lower() for word in ['snake', 'moved away', 'safe distance', 'location', 'area']):
            available_questions = [q for q in first_questions if q not in current_context['asked_questions']]
            if not available_questions:
                available_questions = first_questions
            new_question = random.choice(available_questions)
        
        # Track the question
        current_context['asked_questions'].add(new_question)
        current_context['last_question'] = new_question
        
        return new_question
        
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
                'stretcher_step': 0
            }
        
        current_state = conversation_state[sender]
        
        # Check if this is the first user message
        is_first_message = request.json.get('is_first_message', False)
        
        if is_first_message:
            # Generate a variation of the initial message using Gemini
            initial_prompt = f"""Based on these snake bite first aid guidelines, generate a variation of this initial message:
{who_guidelines}

Original message:
Move them away from the snake. Remove any tight items like rings or bracelets. Keep them calm and still.
Keep their leg still and straight. Don't tie anything around it or try to cut or suck the bite.
If transport is far, make a stretcher using a tarp, rope, or jackets. Get them to a health facility ASAP.
If they feel dizzy or vomit, lay them on their left side. Watch their breathing and be ready to help if needed.

Rules:
1. Keep the same 4 key points but rephrase them
2. Maintain the same order of information
3. Keep the same level of detail
4. Make it sound natural and conversational
5. Don't add or remove any critical information
6. Don't use any prefixes like "SnakeAid:"

Generate a variation of the message:"""
            
            try:
                response = model.generate_content(initial_prompt)
                initial_response = response.text.strip()
                
                # Generate a follow-up question
                follow_up = generate_follow_up_question("", current_state)
                return f"{initial_response}\n\n{follow_up}"
            except Exception as e:
                # Fallback to original message if Gemini fails
                initial_response = """Move them away from the snake. Remove any tight items like rings or bracelets. Keep them calm and still.
Keep their leg still and straight. Don't tie anything around it or try to cut or suck the bite.
If transport is far, make a stretcher using a tarp, rope, or jackets. Get them to a health facility ASAP.
If they feel dizzy or vomit, lay them on their left side. Watch their breathing and be ready to help if needed."""
                follow_up = generate_follow_up_question("", current_state)
                return f"{initial_response}\n\n{follow_up}"
        
        # For subsequent messages, evaluate response and generate contextual response
        is_affirmative, is_negative, needs_help = evaluate_response(message, current_state)
        
        response_prompt = f"""Based ONLY on these guidelines, generate a SHORT, conversational response:

{who_guidelines}

{stretcher_methods}

User message: {message}
User response type: {"positive" if is_affirmative else "negative" if is_negative else "needs help" if needs_help else "neutral"}
Current topic: {current_state.get('current_topic', 'general')}

RULES:
- Keep response under 2-3 sentences
- Only use information from the guidelines
- Be conversational but focused on first aid
- If they're making a stretcher, check their progress and offer specific guidance
- If they seem unsure, ask for clarification
- Never invent medical advice not in the guidelines
- Never ask about moving away from the snake or snake location

Generate natural response:"""
        
        try:
            response = model.generate_content(response_prompt)
            response_text = response.text.strip()
            
            # If response seems to go beyond our knowledge, use safe fallback
            if len(response_text.split()) > 50 or any(keyword in response_text.lower() for keyword in ['antivenom', 'hospital', 'doctor', 'medicine', 'treatment']):
                response_text = "Keep the person calm and still. Continue monitoring their condition."
            
            # Generate appropriate follow-up
            follow_up = generate_follow_up_question(message, current_state)
            
            return f"{response_text}\n\n{follow_up}"
            
        except Exception as e:
            return "Keep monitoring the person's condition. Seek medical help as soon as possible."
            
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