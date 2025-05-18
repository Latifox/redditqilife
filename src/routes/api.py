"""
Routes API pour le bot Reddit.
"""
import json
import logging
from flask import Blueprint, request, jsonify
from src.models.reddit_bot import RedditBot
from src.models.database import Database

# Configuration du logging
logger = logging.getLogger("RedditBotAPI")

# Création du blueprint
api_bp = Blueprint('api', __name__)

# Instance de la base de données
db = Database()

# Clé API pour sécuriser les endpoints (optionnelle)
API_KEY = None  # Clé API désactivée par défaut

def get_bot_instance():
    """Récupère l'instance du bot Reddit depuis l'application Flask."""
    from src.main import get_bot_instance as get_bot
    return get_bot()

def require_api_key(f):
    """Décorateur pour exiger une clé API valide (désactivé)."""
    def decorated_function(*args, **kwargs):
        # Si la vérification de la clé API est désactivée, on passe directement à la fonction
        if API_KEY is None:
            return f(*args, **kwargs)
        
        # Récupérer la clé API depuis les en-têtes
        api_key = request.headers.get('X-API-Key')
        
        # Vérifier si la clé API est valide
        if api_key != API_KEY:
            logger.warning(f"Tentative d'accès non autorisé à l'API depuis {request.remote_addr}")
            return jsonify({"error": "Clé API non valide ou manquante"}), 401
        
        return f(*args, **kwargs)
    
    # Renommer la fonction pour éviter les problèmes avec Flask
    decorated_function.__name__ = f.__name__
    return decorated_function

@api_bp.route('/status', methods=['GET'])
@require_api_key
def get_status():
    """Récupère le statut actuel du bot."""
    try:
        bot = get_bot_instance()
        
        # Récupérer les statistiques
        status = {
            "active": bot.active,
            "dry_run": bot.dry_run,
            "comments_posted_today": bot.comments_posted_today,
            "total_comments_posted": bot.total_comments_posted,
            "monitored_subreddits": bot.subreddits,
            "active_hours": f"{bot.active_hours_start}h-{bot.active_hours_end}h",
            "last_comment_time": bot.last_comment_time
        }
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/start', methods=['POST'])
@require_api_key
def start_bot():
    """Démarre le bot."""
    try:
        bot = get_bot_instance()
        bot.active = True
        
        logger.info("Bot démarré via API")
        return jsonify({"success": True, "message": "Bot démarré"})
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du bot: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/stop', methods=['POST'])
@require_api_key
def stop_bot():
    """Arrête le bot."""
    try:
        bot = get_bot_instance()
        bot.active = False
        
        logger.info("Bot arrêté via API")
        return jsonify({"success": True, "message": "Bot arrêté"})
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du bot: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/run', methods=['POST'])
@require_api_key
def run_bot_cycle():
    """Exécute un cycle manuel du bot."""
    try:
        bot = get_bot_instance()
        stats = bot.monitor_subreddits()
        
        logger.info("Cycle manuel exécuté via API")
        return jsonify({
            "success": True,
            "message": "Cycle manuel exécuté",
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du cycle manuel: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/logs', methods=['GET'])
@require_api_key
def get_logs():
    """Récupère les logs du bot."""
    try:
        # Lire les logs depuis le fichier
        with open("app.log", "r") as f:
            logs = f.readlines()
        
        # Limiter à 100 dernières lignes
        logs = logs[-100:]
        
        return jsonify({"logs": logs})
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des logs: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/config', methods=['GET'])
@require_api_key
def get_config():
    """Récupère la configuration actuelle du bot."""
    try:
        bot = get_bot_instance()
        
        config = {
            "subreddits": bot.subreddits,
            "active_hours_start": bot.active_hours_start,
            "active_hours_end": bot.active_hours_end,
            "min_post_score": bot.min_post_score,
            "max_post_age_hours": bot.max_post_age_hours,
            "comment_rate_limit_seconds": bot.comment_rate_limit_seconds,
            "forbidden_keywords": bot.forbidden_keywords,
            "dry_run": bot.dry_run
        }
        
        return jsonify({"config": config})
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la configuration: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/config', methods=['POST'])
@require_api_key
def update_config():
    """Met à jour la configuration du bot."""
    try:
        data = request.json
        if not data or "config" not in data:
            return jsonify({"error": "Données de configuration manquantes"}), 400
        
        config = data["config"]
        bot = get_bot_instance()
        
        # Mettre à jour la configuration
        bot.subreddits = config.get("subreddits", bot.subreddits)
        bot.active_hours_start = config.get("active_hours_start", bot.active_hours_start)
        bot.active_hours_end = config.get("active_hours_end", bot.active_hours_end)
        bot.min_post_score = config.get("min_post_score", bot.min_post_score)
        bot.max_post_age_hours = config.get("max_post_age_hours", bot.max_post_age_hours)
        bot.comment_rate_limit_seconds = config.get("comment_rate_limit_seconds", bot.comment_rate_limit_seconds)
        bot.forbidden_keywords = config.get("forbidden_keywords", bot.forbidden_keywords)
        bot.dry_run = config.get("dry_run", bot.dry_run)
        
        # Sauvegarder la configuration dans la base de données
        db.save_config("bot_config", config)
        
        logger.info("Configuration mise à jour via API")
        return jsonify({"success": True, "message": "Configuration mise à jour"})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la configuration: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/products', methods=['GET'])
@require_api_key
def get_products():
    """Récupère les produits."""
    try:
        products = db.get_all_products()
        return jsonify({"products": products})
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des produits: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/products', methods=['POST'])
@require_api_key
def update_products():
    """Met à jour les produits."""
    try:
        data = request.json
        if not data or "products" not in data:
            return jsonify({"error": "Données de produits manquantes"}), 400
        
        products = data["products"]
        
        # Sauvegarder chaque produit
        for product_id, product_data in products.items():
            db.save_product(product_id, product_data)
        
        logger.info("Produits mis à jour via API")
        return jsonify({"success": True, "message": "Produits mis à jour"})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des produits: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/personas', methods=['GET'])
@require_api_key
def get_personas():
    """Récupère les personas."""
    try:
        personas = db.get_all_personas()
        return jsonify({"personas": personas})
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des personas: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/personas', methods=['POST'])
@require_api_key
def update_personas():
    """Met à jour les personas."""
    try:
        data = request.json
        if not data or "personas" not in data:
            return jsonify({"error": "Données de personas manquantes"}), 400
        
        personas = data["personas"]
        
        # Sauvegarder chaque persona
        for persona_id, persona_data in personas.items():
            db.save_persona(persona_id, persona_data)
        
        logger.info("Personas mis à jour via API")
        return jsonify({"success": True, "message": "Personas mis à jour"})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des personas: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Récupère les statistiques du bot."""
    try:
        # Pour l'instant, on renvoie des statistiques fictives
        # Dans une version réelle, ces données viendraient de la base de données
        
        stats = {
            "latest_report": {
                "date": "18/05/2025",
                "comments_posted_today": 12,
                "total_comments_posted": 247,
                "active_subreddits": ["python", "programming", "technology"],
                "products_used": {
                    "product1": {
                        "name": "Produit Exemple 1",
                        "count": 145
                    },
                    "product2": {
                        "name": "Produit Exemple 2",
                        "count": 102
                    }
                }
            }
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        return jsonify({"error": str(e)}), 500

# Endpoints pour la gestion des identifiants

@api_bp.route('/credentials', methods=['GET'])
@require_api_key
def get_credentials():
    """Récupère les identifiants (masqués pour la sécurité)."""
    try:
        credentials = {}
        
        # Reddit credentials
        reddit_client_id = db.get_credential("reddit_client_id")
        reddit_client_secret = db.get_credential("reddit_client_secret")
        reddit_username = db.get_credential("reddit_username")
        reddit_password = db.get_credential("reddit_password")
        reddit_user_agent = db.get_credential("reddit_user_agent")
        
        # OpenAI credentials
        openai_api_key = db.get_credential("openai_api_key")
        openai_model = db.get_credential("openai_model")
        
        # Masquer les secrets pour la sécurité
        if reddit_client_id:
            credentials["reddit_client_id"] = reddit_client_id
        
        if reddit_client_secret:
            # Masquer le secret, ne renvoyer que l'indication qu'il existe
            credentials["reddit_client_secret"] = "••••••••"
        
        if reddit_username:
            credentials["reddit_username"] = reddit_username
        
        if reddit_password:
            # Masquer le mot de passe, ne renvoyer que l'indication qu'il existe
            credentials["reddit_password"] = "••••••••"
        
        if reddit_user_agent:
            credentials["reddit_user_agent"] = reddit_user_agent
        
        if openai_api_key:
            # Masquer la clé API, ne renvoyer que l'indication qu'elle existe
            credentials["openai_api_key"] = "••••••••"
        
        if openai_model:
            credentials["openai_model"] = openai_model
        
        return jsonify(credentials)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des identifiants: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/credentials/reddit', methods=['POST'])
@require_api_key
def update_reddit_credentials():
    """Met à jour les identifiants Reddit."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Données d'identifiants manquantes"}), 400
        
        # Sauvegarder les identifiants Reddit
        if "reddit_client_id" in data and data["reddit_client_id"]:
            db.save_credential("reddit_client_id", data["reddit_client_id"])
        
        if "reddit_client_secret" in data and data["reddit_client_secret"]:
            db.save_credential("reddit_client_secret", data["reddit_client_secret"])
        
        if "reddit_username" in data and data["reddit_username"]:
            db.save_credential("reddit_username", data["reddit_username"])
        
        if "reddit_password" in data and data["reddit_password"]:
            db.save_credential("reddit_password", data["reddit_password"])
        
        if "reddit_user_agent" in data and data["reddit_user_agent"]:
            db.save_credential("reddit_user_agent", data["reddit_user_agent"])
        
        logger.info("Identifiants Reddit mis à jour via API")
        return jsonify({"success": True, "message": "Identifiants Reddit mis à jour"})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des identifiants Reddit: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/credentials/openai', methods=['POST'])
@require_api_key
def update_openai_credentials():
    """Met à jour les identifiants OpenAI."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Données d'identifiants manquantes"}), 400
        
        # Sauvegarder les identifiants OpenAI
        if "openai_api_key" in data and data["openai_api_key"]:
            db.save_credential("openai_api_key", data["openai_api_key"])
        
        if "openai_model" in data and data["openai_model"]:
            db.save_credential("openai_model", data["openai_model"])
        
        logger.info("Identifiants OpenAI mis à jour via API")
        return jsonify({"success": True, "message": "Identifiants OpenAI mis à jour"})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des identifiants OpenAI: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/credentials/test', methods=['POST'])
@require_api_key
def test_credentials():
    """Teste les identifiants Reddit et OpenAI."""
    try:
        # Récupérer les identifiants
        reddit_client_id = db.get_credential("reddit_client_id")
        reddit_client_secret = db.get_credential("reddit_client_secret")
        reddit_username = db.get_credential("reddit_username")
        reddit_password = db.get_credential("reddit_password")
        
        openai_api_key = db.get_credential("openai_api_key")
        
        # Vérifier les identifiants Reddit
        reddit_valid = False
        if reddit_client_id and reddit_client_secret and reddit_username and reddit_password:
            try:
                # Dans une version réelle, on testerait l'authentification Reddit ici
                # Pour l'instant, on considère que les identifiants sont valides s'ils sont tous présents
                reddit_valid = True
            except Exception as e:
                logger.error(f"Erreur lors du test des identifiants Reddit: {e}")
        
        # Vérifier les identifiants OpenAI
        openai_valid = False
        if openai_api_key:
            try:
                # Dans une version réelle, on testerait l'authentification OpenAI ici
                # Pour l'instant, on considère que les identifiants sont valides si la clé API est présente
                openai_valid = True
            except Exception as e:
                logger.error(f"Erreur lors du test des identifiants OpenAI: {e}")
        
        return jsonify({
            "reddit_valid": reddit_valid,
            "openai_valid": openai_valid
        })
    except Exception as e:
        logger.error(f"Erreur lors du test des identifiants: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/credentials/import', methods=['POST'])
@require_api_key
def import_credentials():
    """Importe les identifiants depuis le fichier .env."""
    try:
        success = db.import_from_json_files()
        
        if success:
            logger.info("Identifiants importés depuis .env")
            return jsonify({"success": True, "message": "Identifiants importés avec succès"})
        else:
            return jsonify({"error": "Erreur lors de l'importation des identifiants"}), 500
    except Exception as e:
        logger.error(f"Erreur lors de l'importation des identifiants: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/credentials/export', methods=['POST'])
@require_api_key
def export_credentials():
    """Exporte les identifiants vers le fichier .env."""
    try:
        success = db.export_to_json_files()
        
        if success:
            logger.info("Identifiants exportés vers .env")
            return jsonify({"success": True, "message": "Identifiants exportés avec succès"})
        else:
            return jsonify({"error": "Erreur lors de l'exportation des identifiants"}), 500
    except Exception as e:
        logger.error(f"Erreur lors de l'exportation des identifiants: {e}")
        return jsonify({"error": str(e)}), 500
