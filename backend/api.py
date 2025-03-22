from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from PIL import Image
import google.generativeai as genai
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Gemini
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("Warning: GEMINI_API_KEY not found in environment variables. Image analysis will not work.")
else:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro-vision')

# Initialize snake database
snakes_db = {
    "snakes": [
        {
            "id": 1,
            "name": "Fer-de-Lance",
            "scientific_name": "Bothrops asper",
            "color": "brown",
            "size": "large",
            "venom": "hemotoxic",
            "symptoms": ["swelling", "pain", "bruising", "necrosis"],
            "first_aid": "1. Keep calm\n2. Immobilize limb\n3. Remove jewelry\n4. Seek immediate hospital\n5. Do NOT apply ice or tourniquet",
            "habitat": "Lowland forests"
        },
        {
            "id": 2,
            "name": "Coral Snake",
            "scientific_name": "Micrurus spp.",
            "color": "red, black, yellow",
            "size": "small",
            "venom": "neurotoxic",
            "symptoms": ["blurred vision", "paralysis", "difficulty breathing"],
            "first_aid": "1. Keep victim still and calm\n2. Apply pressure bandage\n3. Keep warm\n4. Immediate antivenom\n5. Monitor breathing",
            "habitat": "Tropical forests"
        },
        {
            "id": 3,
            "name": "Bushmaster",
            "scientific_name": "Lachesis muta",
            "color": "brown, patterned",
            "size": "large",
            "venom": "hemotoxic",
            "symptoms": ["pain", "bleeding", "shock", "tissue damage"],
            "first_aid": "1. Keep calm\n2. Immobilize limb\n3. Remove jewelry\n4. Seek immediate hospital\n5. Monitor for shock",
            "habitat": "Tropical rainforests"
        },
        {
            "id": 4,
            "name": "Eyelash Viper",
            "scientific_name": "Bothriechis schlegelii",
            "color": "yellow, green, brown",
            "size": "small",
            "venom": "hemotoxic",
            "symptoms": ["swelling", "pain", "bruising", "tissue necrosis"],
            "first_aid": "1. Keep calm\n2. Immobilize bite area\n3. Remove constricting items\n4. Seek immediate medical attention",
            "habitat": "Tropical forests, arboreal"
        },
        {
            "id": 5,
            "name": "Hog-nosed Pit Viper",
            "scientific_name": "Porthidium nasutum",
            "color": "brown, gray",
            "size": "small",
            "venom": "mildly hemotoxic",
            "symptoms": ["localized swelling", "pain", "mild necrosis"],
            "first_aid": "1. Clean wound\n2. Immobilize area\n3. Seek medical attention\n4. Monitor symptoms",
            "habitat": "Forest floor"
        },
        {
            "id": 6,
            "name": "Neotropical Rattlesnake",
            "scientific_name": "Crotalus durissus",
            "color": "brown, tan, black bands",
            "size": "medium",
            "venom": "neurotoxic",
            "symptoms": ["muscle weakness", "respiratory distress", "blurred vision"],
            "first_aid": "1. Keep victim still\n2. Remove constricting items\n3. Monitor breathing\n4. Immediate medical attention",
            "habitat": "Dry forest, grasslands"
        },
        {
            "id": 7,
            "name": "Jumping Pit Viper",
            "scientific_name": "Atropoides mexicanus",
            "color": "brown, dark markings",
            "size": "medium",
            "venom": "hemotoxic",
            "symptoms": ["pain", "swelling", "bruising"],
            "first_aid": "1. Immobilize limb\n2. Keep calm\n3. Remove jewelry\n4. Seek medical help",
            "habitat": "Forest floor"
        },
        {
            "id": 8,
            "name": "False Fer-de-Lance",
            "scientific_name": "Xenodon rabdocephalus",
            "color": "brown, gray, patterned",
            "size": "medium",
            "venom": "mild hemotoxic",
            "symptoms": ["swelling", "mild pain", "nausea"],
            "first_aid": "1. Clean wound\n2. Monitor symptoms\n3. Seek medical attention",
            "habitat": "Forest floor, agricultural areas"
        },
        {
            "id": 9,
            "name": "Green Vine Snake",
            "scientific_name": "Oxybelis fulgidus",
            "color": "bright green",
            "size": "medium",
            "venom": "mildly toxic",
            "symptoms": ["minor swelling", "redness", "localized pain"],
            "first_aid": "1. Clean wound\n2. Apply antiseptic\n3. Monitor for allergic reaction",
            "habitat": "Trees and bushes"
        },
        {
            "id": 10,
            "name": "Boa Constrictor",
            "scientific_name": "Boa constrictor",
            "color": "brown, tan, black markings",
            "size": "large",
            "venom": "non-venomous",
            "symptoms": ["constriction injuries", "bruising", "shortness of breath if squeezed"],
            "first_aid": "1. Clean any bite wounds\n2. Apply antiseptic\n3. Monitor for infection",
            "habitat": "Various habitats"
        },
        {
            "id": 11,
            "name": "Terciopelo",
            "scientific_name": "Bothrops asper",
            "color": "brown, patterned",
            "size": "large",
            "venom": "hemotoxic",
            "symptoms": ["severe pain", "swelling", "bleeding", "tissue damage"],
            "first_aid": "1. Keep calm\n2. Immobilize limb\n3. Remove jewelry\n4. Seek immediate hospital",
            "habitat": "Lowland forests"
        }
    ]
}

# API Routes
@app.route('/')
def home():
    return jsonify({
        "message": "Snake Identification API",
        "endpoints": {
            "GET /api/snakes": "Get all snakes",
            "GET /api/snakes/<id>": "Get snake by ID",
            "GET /api/snakes/search?q=<query>": "Search snakes by name/color",
            "GET /api/symptoms/search?symptoms=<symptom1>&symptoms=<symptom2>": "Search snakes by symptoms",
            "POST /api/snakes/analyze": "Analyze snake image"
        }
    })

@app.route('/api/snakes', methods=['GET'])
def get_all_snakes():
    return jsonify(snakes_db["snakes"])

@app.route('/api/snakes/<int:snake_id>', methods=['GET'])
def get_snake(snake_id):
    snake = next((s for s in snakes_db["snakes"] if s["id"] == snake_id), None)
    if snake is None:
        return jsonify({"error": "Snake not found"}), 404
    return jsonify(snake)

@app.route('/api/snakes/search', methods=['GET'])
def search_snakes():
    query = request.args.get('q', '').lower()
    results = [
        snake for snake in snakes_db["snakes"]
        if query in snake["name"].lower() or
           query in snake["scientific_name"].lower() or
           query in snake["color"].lower()
    ]
    return jsonify(results)

@app.route('/api/snakes/analyze', methods=['POST'])
def analyze_snake():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
        
    try:
        image_file = request.files['image']
        
        # Save image to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            image_file.save(temp_file.name)
            img = Image.open(temp_file.name)
        
        # Prepare prompt for snake identification
        prompt = """Analyze this image and identify the snake species. 
        Focus on key identifying features like color patterns, head shape, and body structure. 
        If you can identify the species, provide the common name. 
        If you're not certain, indicate that the snake is unidentified."""
        
        # Generate response using Gemini
        if 'model' in locals():
            response = model.generate_content([prompt, img])
            snake_name = response.text.strip()
        else:
            return jsonify({
                'warning': 'GEMINI_API_KEY not found. Image analysis not available.',
                'analysis': 'Unidentified snake. First aid: Keep calm, immobilize area, seek medical help.'
            })
        
        # Search for snake in database
        snake = next((s for s in snakes_db["snakes"] if s["name"].lower() in snake_name.lower()), None)
        
        if snake:
            return jsonify({
                'identification': snake["name"],
                'details': snake
            })
        else:
            return jsonify({
                'warning': 'Unidentified snake. First aid: Keep calm, immobilize area, seek medical help.',
                'analysis': snake_name
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary file
        if 'temp_file' in locals():
            os.unlink(temp_file.name)

@app.route('/api/symptoms/search', methods=['GET'])
def search_by_symptoms():
    symptoms = request.args.getlist('symptoms')
    if not symptoms:
        return jsonify({"error": "No symptoms provided"}), 400
    
    matching_snakes = []
    for snake in snakes_db["snakes"]:
        if any(symptom.lower() in [s.lower() for s in snake["symptoms"]] for symptom in symptoms):
            matching_snakes.append(snake)
    
    return jsonify(matching_snakes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
