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
If they feel dizzy or vomit, position them on their left side and monitor their breathing closely.""",
    
    """Begin by moving them away from the snake. Take off any constricting items like rings or bracelets.
Help them remain calm and motionless, keeping the affected limb straight and still.
If transport is needed, create a stretcher from available materials and head to medical care right away.
Watch for signs of dizziness or vomiting - if these occur, lay them on their left side and monitor breathing.""",
    
    """First step: get them away from the snake. Remove any tight items near the bite area.
Keep them as still as possible, with the affected limb straight and immobilized.
For longer distances, make a stretcher from tarp, rope, or jackets. Get to medical help immediately.
If they become dizzy or vomit, place them on their left side and watch their breathing carefully.""",
    
    """Start by ensuring they're away from the snake. Take off any constricting jewelry or clothing.
Help them stay calm and completely still, with the bitten limb straight and supported.
If you need to transport them, create a stretcher from available materials and get to medical care quickly.
Watch for dizziness or vomiting - if these occur, position them on their left side and monitor breathing.""",
    
    """First priority: move them away from the snake. Remove any tight items from around the bite area.
Keep them motionless and calm, with the affected limb straight and still.
For transport, make a stretcher from tarp, rope, or jackets if needed. Head to medical help right away.
If they feel dizzy or vomit, lay them on their left side and keep monitoring their breathing closely.""",
    
    """Begin by getting them away from the snake. Take off any constricting items like rings or bracelets.
Help them remain calm and completely still, with the bitten limb straight and supported.
If transport is needed, create a stretcher from available materials and get to medical care immediately.
Watch for signs of dizziness or vomiting - if these occur, place them on their left side and monitor breathing."""
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

# Define thematic pathways for questions
question_pathways = {
    'initial_assessment': {
        'name': 'Initial Assessment',
        'questions': [
            "Is the person conscious and able to speak?",
            "How is their breathing? Is it normal?",
            "Can they move the affected limb?",
            "Are they showing any signs of dizziness or confusion?",
            "Is their skin color normal around the bite area?"
        ],
        'next_pathway': 'immediate_care'
    },
    'immediate_care': {
        'name': 'Immediate Care',
        'questions': [
            "Have you removed any tight items like rings or bracelets from around the bite area?",
            "Is the person calm and still?",
            "Has the affected limb been immobilized?",
            "Are they in a comfortable position?",
            "Do they need to be moved to a better location?"
        ],
        'next_pathway': 'transport_prep'
    },
    'transport_prep': {
        'name': 'Transport Preparation',
        'questions': [
            "Do you need help preparing transport to a medical facility?",
            "Do you have materials available to make a stretcher if needed?",
            "Is medical help nearby or will you need to travel far?",
            "Do you have someone to help with transport?",
            "Would you like instructions for making a makeshift stretcher?"
        ],
        'next_pathway': 'monitoring'
    },
    'monitoring': {
        'name': 'Ongoing Monitoring',
        'questions': [
            "Is the person showing any signs of dizziness or vomiting?",
            "How is their breathing now?",
            "Are they able to stay still and calm?",
            "Is the affected limb still immobilized?",
            "Do they need to be repositioned?"
        ],
        'next_pathway': 'initial_assessment'  # Loop back to initial assessment
    }
}

def get_predefined_response(message, current_state):
    """Generate a response using predefined questions and responses."""
    try:
        # Initialize state if needed
        if 'asked_questions' not in current_state:
            current_state['asked_questions'] = set()
            current_state['completed_actions'] = set()
            current_state['current_pathway'] = 'initial_assessment'
            current_state['pathway_question_index'] = 0
        
        # Get current pathway and question index
        current_pathway = current_state['current_pathway']
        question_index = current_state['pathway_question_index']
        
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
        
        # Get current pathway's questions
        pathway_questions = question_pathways[current_pathway]['questions']
        
        # If we've asked all questions in current pathway, move to next pathway
        if question_index >= len(pathway_questions):
            current_state['current_pathway'] = question_pathways[current_pathway]['next_pathway']
            current_state['pathway_question_index'] = 0
            pathway_questions = question_pathways[current_state['current_pathway']]['questions']
        
        # Get next question from current pathway
        next_question = pathway_questions[question_index]
        
        # Update state
        current_state['asked_questions'].add(next_question)
        current_state['last_question'] = next_question
        current_state['pathway_question_index'] += 1
        
        return f"{response}\n\n{next_question}"
        
    except Exception as e:
        return "How is the person's condition now?"

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
                'stretcher_step': 0,
                'has_shown_initial_message': False,
                'current_pathway': 'initial_assessment',
                'pathway_question_index': 0
            }
        
        current_state = conversation_state[sender]
        
        # Check if this is the first user message and we haven't shown the initial message yet
        is_first_message = request.json.get('is_first_message', False)
        
        if is_first_message and not current_state.get('has_shown_initial_message', False):
            # Use predefined initial message
            initial_response = random.choice(initial_message_variations)
            
            # Get first follow-up question from initial assessment pathway
            first_question = question_pathways['initial_assessment']['questions'][0]
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