import os
import sqlite3
from flask import Flask, request, jsonify
from PIL import Image
import google.generativeai as genai

def create_app(test_config=None):
    app = Flask(__name__)
    
    # Configure application
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'snakes.db'),
        GEMINI_API_KEY=os.environ.get('GEMINI_API_KEY', 'YOUR_API'),
        UPLOAD_FOLDER=os.path.join(app.root_path, 'temp_uploads')
    )

    # Ensure instance and upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize Gemini
    genai.configure(api_key=app.config['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Database setup
    def init_db():
        with app.app_context():
            conn = sqlite3.connect(app.config['DATABASE'])
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS snakes
                        (id INTEGER PRIMARY KEY,
                        common_name TEXT UNIQUE,
                        scientific_name TEXT,
                        venom_type TEXT,
                        first_aid TEXT,
                        habitat TEXT)''')
            
            sample_snakes = [
                ('Terciopelo', 'Bothrops asper', 'Hemotoxic',
                 '1. Keep calm\n2. Immobilize limb\n3. Remove jewelry\n4. Seek immediate hospital',
                 'Lowland forests'),
                ('Coral Snake', 'Micrurus spp.', 'Neurotoxic',
                 '1. Apply pressure bandage\n2. Keep warm\n3. Immediate antivenom',
                 'Tropical forests'),
                ('Boa Constrictor', 'Boa constrictor', 'Non-venomous',
                 '1. Clean wound\n2. Apply antiseptic\n3. Monitor for infection',
                 'Various habitats')
            ]
            
            # Upsert operation
            c.executemany('''INSERT OR REPLACE INTO snakes 
                            (common_name, scientific_name, venom_type, first_aid, habitat)
                            VALUES (?,?,?,?,?)''', sample_snakes)
            conn.commit()
            conn.close()

    if not os.path.exists(app.config['DATABASE']):
        init_db()

    # Routes
    @app.route('/')
    def home():
        return "Snake Identification API - POST snake images to /analyze endpoint"

    @app.route('/analyze', methods=['POST'])
    def handle_analysis():
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
            
        try:
            image_file = request.files['image']
            text_description = request.form.get('description', '')
            
            # Secure filename handling
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
            image_file.save(temp_path)
            
            # Image analysis
            snake_name = analyze_snake(temp_path)
            
            # Database lookup
            conn = sqlite3.connect(app.config['DATABASE'])
            c = conn.cursor()
            
            if not snake_name or snake_name == 'Unknown':
                return jsonify({
                    'warning': 'Unidentified snake. First aid: Keep calm, immobilize area, seek medical help.'
                })
            
            c.execute('SELECT * FROM snakes WHERE common_name = ?', (snake_name,))
            result = c.fetchone()
            
            if not result:
                return jsonify({'error': 'Snake data not found'}), 404
            
            response = {
                'identification': snake_name,
                'details': {
                    'scientific_name': result[2],
                    'venom_type': result[3],
                    'habitat': result[5]
                },
                'first_aid': result[4].split('\n'),
                'user_description': text_description
            }
            
            return jsonify(response)
            
        except Exception as e:
            app.logger.error(f"Error processing request: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
            
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            conn.close()

    def analyze_snake(image_path):
        """Analyze image using Gemini"""
        try:
            img = Image.open(image_path)
            response = model.generate_content([
                "Identify this Costa Rican snake. Reply ONLY with common name from: Terciopelo, Coral Snake, Boa Constrictor, Unknown",
                img
            ])
            return response.text.strip()
        except Exception as e:
            app.logger.error(f"Image analysis failed: {str(e)}")
            return None

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)