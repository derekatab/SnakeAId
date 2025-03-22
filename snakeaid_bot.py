from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from fuzzywuzzy import process
import pandas as pd

app = Flask(__name__)

# Sample snake database
snake_data = [
    {
        "name": "Fer-de-Lance", 
        "color": "brown", 
        "size": "large", 
        "venom": "hemotoxic", 
        "symptoms": ["swelling", "pain", "bruising", "necrosis"]
    },
    {
        "name": "Coral Snake", 
        "color": "red, black, yellow", 
        "size": "small", 
        "venom": "neurotoxic", 
        "symptoms": ["blurred vision", "paralysis", "difficulty breathing"]
    },
    {
        "name": "Bushmaster", 
        "color": "brown, patterned", 
        "size": "large", 
        "venom": "hemotoxic", 
        "symptoms": ["pain", "bleeding", "shock", "tissue damage"]
    },
    {
        "name": "Eyelash Viper", 
        "color": "yellow, green, brown", 
        "size": "small", 
        "venom": "hemotoxic", 
        "symptoms": ["swelling", "pain", "bruising", "tissue necrosis"]
    },
    {
        "name": "Hog-nosed Pit Viper", 
        "color": "brown, gray", 
        "size": "small", 
        "venom": "mildly hemotoxic", 
        "symptoms": ["localized swelling", "pain", "mild necrosis"]
    },
    {
        "name": "Neotropical Rattlesnake", 
        "color": "brown, tan, black bands", 
        "size": "medium", 
        "venom": "neurotoxic", 
        "symptoms": ["muscle weakness", "respiratory distress", "blurred vision"]
    },
    {
        "name": "Jumping Pit Viper", 
        "color": "brown, dark markings", 
        "size": "medium", 
        "venom": "hemotoxic", 
        "symptoms": ["pain", "swelling", "bruising"]
    },
    {
        "name": "False Fer-de-Lance", 
        "color": "brown, gray, patterned", 
        "size": "medium", 
        "venom": "mild hemotoxic", 
        "symptoms": ["swelling", "mild pain", "nausea"]
    },
    {
        "name": "Green Vine Snake", 
        "color": "bright green", 
        "size": "medium", 
        "venom": "mildly toxic", 
        "symptoms": ["minor swelling", "redness", "localized pain"]
    },
    {
        "name": "Boa Constrictor", 
        "color": "brown, tan, black markings", 
        "size": "large", 
        "venom": "non-venomous", 
        "symptoms": ["constriction injuries", "bruising", "shortness of breath if squeezed"]
    }
]

# Convert to DataFrame
df = pd.DataFrame(snake_data)

# Step tracking for conversation flow
user_sessions = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.form.get("Body", "").lower()
    sender = request.form.get("From")  # Fix sender
    response = MessagingResponse()
    msg = response.message()
    msg.body("Hello! This is a test response.")
    return str(response), 200

    
    # Initialize user session if not exists
    if sender not in user_sessions:
        user_sessions[sender] = {"step": 0, "description": {}, "symptoms": []}

    step = user_sessions[sender]["step"]

    # **Conversation Flow**
    if step == 0:
        msg.body("🐍 What was the snake's color? (e.g., brown, black, red, yellow, patterned)")
        user_sessions[sender]["step"] = 1

    elif step == 1:
        user_sessions[sender]["description"]["color"] = incoming_msg
        msg.body("🐍 What was the snake's size? (small, medium, large)")
        user_sessions[sender]["step"] = 2

    elif step == 2:
        user_sessions[sender]["description"]["size"] = incoming_msg
        msg.body("⚠️ What symptoms do you have? (List symptoms like pain, swelling, blurred vision)")
        user_sessions[sender]["step"] = 3

    elif step == 3:
        # Get new additional symptoms and combine with existing ones
        new_symptoms = [s.strip() for s in incoming_msg.split(",")]
        user_sessions[sender]["symptoms"].extend(new_symptoms)  # Combine with existing symptoms
        symptoms = user_sessions[sender]["symptoms"]  # Use combined symptoms list

        # **Matching the snake type**
        matched_snake = None
        highest_score = 0

        for _, row in df.iterrows():
            color_score = process.extractOne(user_sessions[sender]["description"]["color"], row["color"].split(", "), score_cutoff=50)
            size_match = row["size"] == user_sessions[sender]["description"]["size"]
            symptom_match = any(symptom in list(row["symptoms"]) for symptom in symptoms)

            if color_score and size_match and symptom_match:
                matched_snake = row.to_dict()  # Convert Series to dict
                highest_score = color_score[1]
        # Check if `matched_snake` is not None
        if matched_snake:
            msg.body(f"🩸 This could be a {matched_snake['name']} ({matched_snake['venom']} venom).\n"
                f"🚑 First Aid: {first_aid_advice(matched_snake['venom'])}\n"
                f"💡 Do you have other symptoms? (yes/no)")
            user_sessions[sender]["step"] = 4  # Continue conversation
        else:
            msg.body("❓ I couldn't identify the snake, but seek urgent medical help immediately!")
            user_sessions[sender] = {"step": 0, "description": {}, "symptoms": []}  # Reset session


    elif step == 4:
        if incoming_msg in ["yes", "y"]:
            msg.body("⚠️ List any additional symptoms.")
            user_sessions[sender]["step"] = 3  # Go back to symptom collection
        else:
            msg.body("🚑 Seek medical help immediately. Stay calm and limit movement.")
            user_sessions[sender] = {"step": 0, "description": {}, "symptoms": []}  # Reset session

    return str(response), 200

# **First Aid Recommendations**
def first_aid_advice(venom_type):
    if venom_type == "hemotoxic":
        return (
            "🩸 **Hemotoxic Venom First Aid:**\n"
            "- **Do NOT cut or suck the wound.** \n"
            "- **Keep the bite area immobilized** and positioned **below heart level** to slow venom spread.\n"
            "- **Remove tight clothing, jewelry, or accessories** near the bite, as swelling will occur.\n"
            "- **Do NOT apply ice or a tourniquet**, as these can worsen tissue damage.\n"
            "- **Monitor for signs of shock**, such as pale skin, rapid breathing, or dizziness. Keep the person lying down and calm.\n"
        )

    elif venom_type == "neurotoxic":
        return (
            "🧠 **Neurotoxic Venom First Aid:**\n"
            "- **Keep the victim as still and calm as possible** to slow the spread of venom.\n"
            "- **Do NOT apply a tourniquet or ice**, as these can cause more harm than good.\n"
            "- **If the person has trouble breathing, provide CPR if trained.** \n"
            "- **Lay the person on their side** to prevent choking if vomiting occurs.\n"
            "- **Do NOT give food, water, or medication**, as the venom may impair swallowing.\n"
            "- **Seek medical help IMMEDIATELY, even if symptoms are mild.** Some neurotoxic bites worsen over time."
        )

    else:
        return (
            "🚑 **General Snakebite First Aid:**\n"
            "- **Limit movement and keep the bite area immobilized** to reduce venom spread.\n"
            "- **Remove rings, watches, and tight clothing** before swelling starts.\n"
            "- **Do NOT attempt to suck, cut, or apply ice/tourniquets**—these can cause more damage.\n"
            "- **Call emergency services or head to the nearest hospital immediately.**"
        )

if __name__ == "__main__":
    app.run(port=5000, debug=True)