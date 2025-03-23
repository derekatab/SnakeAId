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
GEMINI_API_KEY = 'AIzaSyC91lYMZjNiUw_AuzzniWHqDqWVeH0De9Q'
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

# Global variable to track conversation state
conversation_state = {}

def generate_follow_up_question(message, current_context, who_guidelines, stretcher_methods):
    """
    Dynamically generate a follow-up question based on the current conversation context
    and the available WHO guidelines.
    
    Args:
        message (str): The previous message from the user
        current_context (dict): Current conversation state
        who_guidelines (str): WHO first aid guidelines context
        stretcher_methods (str): Makeshift stretcher methods context
    
    Returns:
        str: A context-aware follow-up question
    """
    try:
        # Comprehensive context for question generation
        context_prompt = f"""You are an emergency snake bite first aid AI assistant. 
        Generate a precise, context-aware follow-up question based strictly on the WHO guidelines.

        AVAILABLE CONTEXT:
        {who_guidelines}
        {stretcher_methods}

        CURRENT CONVERSATION CONTEXT:
        Previous Message: {message}
        Current Conversation Stage: {current_context['stage']}
        Last Action: {current_context['last_action']}

        QUESTION GENERATION GUIDELINES:
        - Base the question ONLY on the provided WHO guidelines
        - Do not invent or speculate beyond the given context
        - Make the question specific and actionable
        - Focus on immediate first aid and safety
        - Aim to gather critical information for next steps
        - Keep the question concise and clear

        Generate a single, targeted follow-up question."""
        
        # Generate follow-up question using Gemini
        response = model.generate_content(context_prompt)
        
        # Ensure a valid question is generated
        follow_up_question = response.text.strip() if response and response.text else (
            "What is the current condition of the victim?"
        )
        
        # Ensure the question ends with a question mark
        if not follow_up_question.endswith('?'):
            follow_up_question += '?'
        
        return follow_up_question
    
    except Exception as e:
        print(f"Error generating follow-up question: {e}")
        return "What is the current condition of the victim?"

def process_user_response(message, current_context, who_guidelines, stretcher_methods):
    """
    Process user's response based on the current conversation context.
    
    Args:
        message (str): User's response message
        current_context (dict): Current conversation state
        who_guidelines (str): WHO first aid guidelines context
        stretcher_methods (str): Makeshift stretcher methods context
    
    Returns:
        tuple: (response_text, updated_context)
    """
    try:
        # Determine follow-up based on conversation flow
        # Prioritize specific actions from WHO guidelines
        specific_actions = [
            ('snake', 'Move away from the snake if still nearby.'),
            ('tight', 'Remove rings, bracelets near the bite area.'),
            ('calm', 'Keep the victim calm. Most snake bites are not immediately fatal.'),
            ('leg', 'Keep the leg still. Do not move or tie anything around it.'),
            ('stretcher', 'Prepare to make a stretcher using tarp, rope, or jackets.'),
            ('dizzy', 'If dizzy or vomiting, lay on left side. Monitor breathing.'),
            ('pain', 'Paracetamol may help with severe local pain.')
        ]
        
        # Find the most relevant action based on the message
        response_text = None
        for keyword, action_text in specific_actions:
            if keyword in message.lower():
                response_text = action_text
                break
        
        # If no specific action found, provide a generic but short guidance
        if not response_text:
            response_text = "Continue to prioritize safety. Keep the victim still and calm."
        
        # Generate a follow-up question
        follow_up_questions = [
            "Are you able to keep the victim still?",
            "What materials do you have nearby?",
            "Can you describe the victim's current condition?",
            "Is help on the way?"
        ]
        
        # Select a follow-up question based on context or randomly
        import random
        follow_up_question = random.choice(follow_up_questions)
        
        # Combine response and follow-up question
        full_response = f"{response_text}\n\n{follow_up_question}"
        
        # Update context if needed
        if 'last_action' in current_context:
            current_context['previous_action'] = current_context['last_action']
        
        return full_response, current_context
    
    except Exception as e:
        print(f"Error processing user response: {e}")
        return "Continue to prioritize the victim's safety. Emergency services should be contacted immediately.", current_context

def generate_response(message, sender=None):
    try:
        # Retrieve or initialize conversation state for this sender
        if sender not in conversation_state:
            conversation_state[sender] = {'stage': 'initial', 'last_action': None, 'conversation_depth': 0}
        
        current_state = conversation_state[sender]
        current_state['conversation_depth'] += 1
        
        # WHO First Aid Guidelines Context
        who_guidelines = """
        First Aid Guidelines for Snake Bites:
        - Immediately move away from the snake bite area
        - If snake is attached, use a stick to make it let go
        - Remove tight items (rings, anklets, bracelets)
        - Reassure the victim
        - Immobilize the person completely
        - Splint the limb
        - Use makeshift stretcher for transport
        - Never use a tight arterial tourniquet
        - Only use Australian Pressure Immobilization Bandage for specific neurotoxic snakes
        - Transport to health facility ASAP
        - Paracetamol may help with local pain
        - If vomiting occurs, place person on left side
        - Monitor airway and breathing
        """
        
        # Makeshift Stretcher Methods Context
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
        
        # Determine response based on conversation state
        if current_state['stage'] == 'initial':
            # Initial snake bite first aid response using the provided template
            # Dynamically adjust pronouns based on message context
            pronouns = 'he/she/they' if 'victim' not in message.lower() else 'them'
            
            response_text = f"""1. Move {pronouns} away from the snake. Remove any tight items like rings or bracelets. Keep {pronouns} calm and still.
2. Keep {pronouns} leg still and straight. Don't tie anything around it or try to cut or suck the bite.
3. If transport is far, make a stretcher using a tarp, rope, or jackets. Get {pronouns} to a health facility ASAP.
4. If {pronouns} feel dizzy or vomit, lay {pronouns} on their left side. Watch {pronouns} breathing and be ready to help if needed."""
            
            # Update conversation state to ask follow-up question
            current_state['stage'] = 'follow_up'
            current_state['last_action'] = 'initial_first_aid'
            
            # Generate a dynamic follow-up question
            follow_up_question = generate_follow_up_question(message, current_state, who_guidelines, stretcher_methods)
            
            # Append the follow-up question
            response_text += f"\n\n{follow_up_question}"
            
            return response_text
        
        elif current_state['stage'] == 'follow_up' or current_state['stage'] == 'detailed_guidance':
            # Process user's response and generate next steps
            response_text, updated_context = process_user_response(
                message, 
                current_state, 
                who_guidelines, 
                stretcher_methods
            )
            
            # Update conversation state
            conversation_state[sender] = updated_context
            
            return response_text
        
        else:
            # Final stage or reset
            return "Emergency number: +999. Seek immediate medical help."
    
    except Exception as e:
        print(f"Unexpected error in generate_response: {str(e)}")
        traceback.print_exc()
        return "1. Call emergency services.\n\n2. Stay calm.\n\n3. Do not move.\n\n4. Wait for help."

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.form.get("Body", "").lower()
    sender = request.form.get("From")
    
    # Generate response using Gemini
    response_text = generate_response(incoming_msg, sender)
    
    print(f"Received WhatsApp message from {sender}: {incoming_msg}")
    print(f"Sending response: {response_text}")
    
    try:
        # Send response directly using Twilio client
        message = client.messages.create(
            body=response_text,
            from_='whatsapp:+14155238886',  # Twilio's WhatsApp sandbox number
            to=sender
        )
        print(f"Message sent with SID: {message.sid}")
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
    
    # Return empty TwiML to acknowledge receipt
    response = MessagingResponse()
    return str(response)

@app.route("/sms", methods=['POST'])
def sms_reply():
    # Get the message from the request
    incoming_msg = request.json.get('Body', '').strip()
    sender = request.json.get('From', 'web-user')
    print(f"\n=== Received message from {sender}: {incoming_msg} ===")

    # Generate response
    response_text = generate_response(incoming_msg)
    print(f"Final response: {response_text}")

    # Return plain text for web requests
    return response_text

if __name__ == "__main__":
    app.run(port=5000, debug=True)