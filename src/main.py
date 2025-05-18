"""
Point d'entrée principal de l'application Flask pour le bot Reddit.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

import logging
import threading
import time
import schedule
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS

from src.routes.api import api_bp
from src.models.reddit_bot import RedditBot

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RedditBotApp")

# Création de l'application Flask
app = Flask(__name__)
CORS(app)  # Activation de CORS pour permettre les requêtes cross-origin

# Enregistrement des blueprints
app.register_blueprint(api_bp, url_prefix='/api')

# Instance du bot Reddit
bot = None

def get_bot_instance():
    """Récupère ou initialise l'instance du bot Reddit."""
    global bot
    if bot is None:
        bot = RedditBot()
    return bot

def scheduler_thread():
    """Thread pour exécuter le planificateur."""
    while True:
        schedule.run_pending()
        time.sleep(1)

def monitor_thread():
    """Thread pour la surveillance des subreddits."""
    bot_instance = get_bot_instance()
    while True:
        if bot_instance.active:
            try:
                bot_instance.monitor_subreddits()
            except Exception as e:
                logger.error(f"Erreur dans le thread de surveillance: {e}")
        time.sleep(60)  # Vérification toutes les minutes

@app.route('/')
def index():
    """Route principale pour servir l'interface utilisateur."""
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Sert les fichiers statiques."""
    return send_from_directory('static', path)

@app.route('/health')
def health_check():
    """Endpoint de vérification de santé pour les systèmes de monitoring."""
    return {"status": "ok"}, 200

def create_sample_data():
    """Crée des données d'exemple si elles n'existent pas."""
    # Produits d'exemple
    if not os.path.exists("products.json"):
        products = {
            "product1": {
                "name": "Produit Exemple 1",
                "description": "Un produit fantastique pour résoudre vos problèmes",
                "url": "https://example.com/product1",
                "keywords": ["problème", "solution", "aide", "outil"]
            },
            "product2": {
                "name": "Produit Exemple 2",
                "description": "Le meilleur outil pour améliorer votre productivité",
                "url": "https://example.com/product2",
                "keywords": ["productivité", "efficacité", "temps", "travail"]
            }
        }
        with open("products.json", 'w', encoding='utf-8') as f:
            import json
            json.dump(products, f, indent=2, ensure_ascii=False)
    
    # Personas d'exemple
    if not os.path.exists("personas.json"):
        personas = {
            "helpful": {
                "name": "Assistant Serviable",
                "tone": "helpful",
                "style": "informative"
            },
            "enthusiastic": {
                "name": "Enthousiaste",
                "tone": "excited",
                "style": "energetic"
            },
            "expert": {
                "name": "Expert",
                "tone": "authoritative",
                "style": "detailed"
            }
        }
        with open("personas.json", 'w', encoding='utf-8') as f:
            import json
            json.dump(personas, f, indent=2, ensure_ascii=False)
    
    # Templates de commentaires d'exemple
    if not os.path.exists("comment_templates.json"):
        templates = {
            "default": "J'ai trouvé une solution à ce problème ! {product_name} m'a vraiment aidé. Vous pouvez le trouver ici : {product_url}",
            "question": "Avez-vous essayé {product_name} ? C'est exactement ce qu'il vous faut pour ce cas. Voici le lien : {product_url}",
            "experience": "J'ai eu le même problème et {product_name} l'a résolu. Je vous le recommande fortement : {product_url}"
        }
        with open("comment_templates.json", 'w', encoding='utf-8') as f:
            import json
            json.dump(templates, f, indent=2, ensure_ascii=False)
    
    # Fichier .env d'exemple
    if not os.path.exists(".env"):
        env_content = """# Configuration Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=RedditBot/1.0

# Configuration OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Configuration du bot
SUBREDDITS=python,programming,technology
ACTIVE_HOURS_START=9
ACTIVE_HOURS_END=22
MIN_POST_SCORE=5
MAX_POST_AGE_HOURS=12
COMMENT_RATE_LIMIT_SECONDS=300
API_KEY=change_this_to_a_secure_key
EXCLUDED_LANGUAGES=arabic,russian
FORBIDDEN_KEYWORDS=nsfw,politics,religion
"""
        with open(".env", 'w', encoding='utf-8') as f:
            f.write(env_content)

# Création des données d'exemple au démarrage
create_sample_data()

if __name__ == '__main__':
    # Démarrage des threads en arrière-plan
    scheduler_thread = threading.Thread(target=scheduler_thread, daemon=True)
    scheduler_thread.start()
    
    monitor_thread = threading.Thread(target=monitor_thread, daemon=True)
    monitor_thread.start()
    
    # Démarrage du serveur Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
