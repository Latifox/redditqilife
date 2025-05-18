"""
Modèle principal du bot Reddit.
"""
import os
import time
import json
import logging
import random
import datetime
import threading
from typing import List, Dict, Any, Optional

import praw
import openai
import schedule
from dotenv import load_dotenv

# Correction de l'import pour éviter l'erreur de module
try:
    from src.models.database import Database
except ModuleNotFoundError:
    from models.database import Database

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RedditBot")

class RedditBot:
    """Classe principale pour le bot Reddit."""
    
    def __init__(self):
        """Initialise le bot Reddit avec les configurations par défaut."""
        logger.info("Initialisation du bot Reddit...")
        # Charger les variables d'environnement depuis .env
        load_dotenv()
        logger.debug("Variables d'environnement chargées depuis .env")
        
        # Initialiser la base de données
        self.db = Database()
        logger.debug("Base de données initialisée")
        
        # Paramètres par défaut
        self.subreddits = ["python", "programming", "technology"]
        self.active_hours_start = 9
        self.active_hours_end = 22
        self.min_post_score = 5
        self.max_post_age_hours = 12
        self.comment_rate_limit_seconds = 300
        self.forbidden_keywords = ["nsfw", "politics", "religion"]
        self.excluded_languages = ["arabic", "russian"]
        
        logger.debug(f"Paramètres par défaut définis: subreddits={self.subreddits}, "
                   f"active_hours={self.active_hours_start}-{self.active_hours_end}, "
                   f"min_score={self.min_post_score}, max_age={self.max_post_age_hours}h, "
                   f"rate_limit={self.comment_rate_limit_seconds}s")
        
        # État du bot
        self.active = False
        self.dry_run = True
        self.comments_posted_today = 0
        self.total_comments_posted = 0
        self.last_comment_time = 0
        
        # Statistiques de traitement
        self.posts_analyzed = 0
        self.posts_filtered = 0
        self.posts_selected = 0
        
        # Charger la configuration depuis la base de données
        self._load_config_from_db()
        
        # Initialiser le client Reddit
        self._init_reddit_client()
        
        # Initialiser le client OpenAI
        self._init_openai_client()
        
        # Charger les produits et personas
        self._load_products_and_personas()
        
        # Configurer le planificateur
        self._setup_scheduler()
        
        logger.info("Bot Reddit initialisé avec les paramètres suivants:")
        logger.info(f"Subreddits: {self.subreddits}")
        logger.info(f"Heures actives: {self.active_hours_start}h-{self.active_hours_end}h")
        logger.info(f"Score minimum: {self.min_post_score}")
        logger.info(f"Âge maximum: {self.max_post_age_hours} heures")
        logger.info(f"Délai entre commentaires: {self.comment_rate_limit_seconds} secondes")
        logger.info(f"Mode dry-run: {self.dry_run}")
        logger.info(f"Mots-clés interdits: {self.forbidden_keywords}")
        logger.info(f"Langues exclues: {self.excluded_languages}")
    
    def _load_config_from_db(self):
        """Charge la configuration depuis la base de données."""
        try:
            config = self.db.get_config("bot_config")
            logger.debug(f"Configuration récupérée de la base de données: {config}")
            
            if config:
                # Log original values before override
                logger.debug(f"Valeurs originales avant chargement DB: subreddits={self.subreddits}, "
                           f"active_hours={self.active_hours_start}-{self.active_hours_end}, "
                           f"min_score={self.min_post_score}, max_age={self.max_post_age_hours}h, "
                           f"rate_limit={self.comment_rate_limit_seconds}s, dry_run={self.dry_run}")
                
                self.subreddits = config.get("subreddits", self.subreddits)
                self.active_hours_start = config.get("active_hours_start", self.active_hours_start)
                self.active_hours_end = config.get("active_hours_end", self.active_hours_end)
                self.min_post_score = config.get("min_post_score", self.min_post_score)
                self.max_post_age_hours = config.get("max_post_age_hours", self.max_post_age_hours)
                self.comment_rate_limit_seconds = config.get("comment_rate_limit_seconds", self.comment_rate_limit_seconds)
                self.forbidden_keywords = config.get("forbidden_keywords", self.forbidden_keywords)
                self.dry_run = config.get("dry_run", self.dry_run)
                
                # Log values after DB override
                logger.debug(f"Valeurs après chargement DB: subreddits={self.subreddits}, "
                           f"active_hours={self.active_hours_start}-{self.active_hours_end}, "
                           f"min_score={self.min_post_score}, max_age={self.max_post_age_hours}h, "
                           f"rate_limit={self.comment_rate_limit_seconds}s, dry_run={self.dry_run}")
                
                logger.info("Configuration chargée depuis la base de données")
            else:
                logger.info("Aucune configuration trouvée en base de données")
                # Si pas de config en DB, essayer de charger depuis .env
                self._load_config_from_env()
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration depuis la base de données: {e}")
            logger.debug(f"Détails de l'erreur: {str(e)}", exc_info=True)
            # Fallback sur .env
            self._load_config_from_env()
    
    def _load_config_from_env(self):
        """Charge la configuration depuis les variables d'environnement."""
        try:
            # Log original values before override
            logger.debug(f"Valeurs originales avant chargement .env: subreddits={self.subreddits}, "
                       f"active_hours={self.active_hours_start}-{self.active_hours_end}, "
                       f"min_score={self.min_post_score}, max_age={self.max_post_age_hours}h, "
                       f"rate_limit={self.comment_rate_limit_seconds}s, dry_run={self.dry_run}")
            
            # Charger les subreddits
            subreddits_env = os.getenv("SUBREDDITS")
            if subreddits_env:
                self.subreddits = subreddits_env.split(",")
                logger.debug(f"Subreddits chargés depuis .env: {self.subreddits}")
            
            # Charger les heures actives
            active_hours_start = os.getenv("ACTIVE_HOURS_START")
            if active_hours_start:
                self.active_hours_start = int(active_hours_start)
                logger.debug(f"Heure de début active chargée depuis .env: {self.active_hours_start}")
            
            active_hours_end = os.getenv("ACTIVE_HOURS_END")
            if active_hours_end:
                self.active_hours_end = int(active_hours_end)
                logger.debug(f"Heure de fin active chargée depuis .env: {self.active_hours_end}")
            
            # Charger les paramètres de filtrage
            min_post_score = os.getenv("MIN_POST_SCORE")
            if min_post_score:
                self.min_post_score = int(min_post_score)
                logger.debug(f"Score minimum chargé depuis .env: {self.min_post_score}")
            
            max_post_age_hours = os.getenv("MAX_POST_AGE_HOURS")
            if max_post_age_hours:
                self.max_post_age_hours = int(max_post_age_hours)
                logger.debug(f"Âge maximum chargé depuis .env: {self.max_post_age_hours}")
            
            # Charger le délai entre commentaires
            comment_rate_limit = os.getenv("COMMENT_RATE_LIMIT_SECONDS")
            if comment_rate_limit:
                self.comment_rate_limit_seconds = int(comment_rate_limit)
                logger.debug(f"Délai entre commentaires chargé depuis .env: {self.comment_rate_limit_seconds}")
            
            # Charger les mots-clés interdits
            forbidden_keywords = os.getenv("FORBIDDEN_KEYWORDS")
            if forbidden_keywords:
                self.forbidden_keywords = forbidden_keywords.split(",")
                logger.debug(f"Mots-clés interdits chargés depuis .env: {self.forbidden_keywords}")
            
            # Charger les langues exclues
            excluded_languages = os.getenv("EXCLUDED_LANGUAGES")
            if excluded_languages:
                self.excluded_languages = excluded_languages.split(",")
                logger.debug(f"Langues exclues chargées depuis .env: {self.excluded_languages}")
            
            # Charger le mode dry-run
            dry_run = os.getenv("DRY_RUN")
            if dry_run is not None:
                self.dry_run = dry_run.lower() == "true"
                logger.debug(f"Mode dry-run chargé depuis .env: {self.dry_run}")
            
            # Log values after ENV override
            logger.debug(f"Valeurs après chargement .env: subreddits={self.subreddits}, "
                       f"active_hours={self.active_hours_start}-{self.active_hours_end}, "
                       f"min_score={self.min_post_score}, max_age={self.max_post_age_hours}h, "
                       f"rate_limit={self.comment_rate_limit_seconds}s, dry_run={self.dry_run}")
            
            logger.info("Configuration chargée depuis les variables d'environnement")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration depuis les variables d'environnement: {e}")
            logger.debug(f"Détails de l'erreur: {str(e)}", exc_info=True)
    
    def _init_reddit_client(self):
        """Initialise le client Reddit avec les identifiants stockés en base de données."""
        try:
            # Récupérer les identifiants depuis la base de données
            client_id = self.db.get_credential("reddit_client_id")
            client_secret = self.db.get_credential("reddit_client_secret")
            username = self.db.get_credential("reddit_username")
            password = self.db.get_credential("reddit_password")
            user_agent = self.db.get_credential("reddit_user_agent") or "RedditBot/1.0"
            
            # Si les identifiants ne sont pas dans la base de données, essayer de les récupérer depuis les variables d'environnement
            if not client_id:
                client_id = os.getenv("REDDIT_CLIENT_ID")
            if not client_secret:
                client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            if not username:
                username = os.getenv("REDDIT_USERNAME")
            if not password:
                password = os.getenv("REDDIT_PASSWORD")
            if not user_agent:
                user_agent = os.getenv("REDDIT_USER_AGENT", "RedditBot/1.0")
            
            # Vérifier si tous les identifiants sont présents
            if client_id and client_secret and username and password:
                logger.info(f"Tentative de connexion à Reddit avec le compte {username} et user agent {user_agent}")
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    username=username,
                    password=password,
                    user_agent=user_agent
                )
                # Vérifier si la connexion est réussie
                username_check = self.reddit.user.me().name
                logger.info(f"Client Reddit initialisé avec succès. Connecté en tant que {username_check}")
                
                # Sauvegarder les identifiants dans la base de données
                self.db.save_credential("reddit_client_id", client_id)
                self.db.save_credential("reddit_client_secret", client_secret)
                self.db.save_credential("reddit_username", username)
                self.db.save_credential("reddit_password", password)
                self.db.save_credential("reddit_user_agent", user_agent)
            else:
                missing = []
                if not client_id: missing.append("client_id")
                if not client_secret: missing.append("client_secret")
                if not username: missing.append("username")
                if not password: missing.append("password")
                
                logger.warning(f"Identifiants Reddit incomplets, le bot fonctionnera en mode limité. Manquant: {', '.join(missing)}")
                self.reddit = None
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Reddit: {e}")
            self.reddit = None
    
    def _init_openai_client(self):
        """Initialise le client OpenAI avec la clé API stockée en base de données."""
        try:
            # Récupérer la clé API depuis la base de données
            api_key = self.db.get_credential("openai_api_key")
            model = self.db.get_credential("openai_model") or "gpt-4o-mini"
            
            # Si la clé API n'est pas dans la base de données, essayer de la récupérer depuis les variables d'environnement
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            if not model:
                model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            
            # Vérifier si la clé API est présente
            if api_key:
                # Initialiser le client OpenAI pour la nouvelle API v1.0.0+
                self.openai_client = openai.OpenAI(api_key=api_key)
                self.openai_model = model
                logger.info(f"Client OpenAI initialisé avec succès. Modèle: {model}")
                
                # Sauvegarder la clé API dans la base de données
                self.db.save_credential("openai_api_key", api_key)
                self.db.save_credential("openai_model", model)
            else:
                logger.warning("Clé API OpenAI manquante, la génération de commentaires sera limitée")
                self.openai_client = None
                self.openai_model = None
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client OpenAI: {e}")
            self.openai_client = None
            self.openai_model = None
    
    def _load_products_and_personas(self):
        """Charge les produits et personas depuis la base de données."""
        try:
            # Charger les produits
            self.products = self.db.get_all_products()
            if not self.products:
                # Si aucun produit n'est trouvé dans la base de données, essayer de les charger depuis le fichier JSON
                if os.path.exists("products.json"):
                    with open("products.json", 'r', encoding='utf-8') as f:
                        self.products = json.load(f)
                        # Sauvegarder les produits dans la base de données
                        for product_id, product_data in self.products.items():
                            self.db.save_product(product_id, product_data)
                else:
                    # Créer des produits par défaut
                    self.products = {
                                    "product1": {
                                        "name": "@qi-coil-mini",
                                        "description": "Compact frequency device that delivers targeted electromagnetic frequencies for wellness and energy balancing.",
                                        "url": "https://qilifestore.com/collections/qi-coils/products/qi-coil-mini",
                                        "keywords": [
                                        "frequency",
                                        "qi coil",
                                        "electromagnetic",
                                        "energy healing",
                                        "portable",
                                        "wellness device",
                                        "stress",
                                        "fatigue",
                                        "energy imbalance",
                                        "sleep issues",
                                        "tension",
                                        "on-the-go",
                                        "balancing",
                                        "relaxation",
                                        "compact"
                                        ]
                                    },
                                    "product2": {
                                        "name": "Qi Coil Mini System with RC1",
                                        "description": "Complete frequency therapy system featuring the Qi Coil Mini with Resonant Console 1 for advanced frequency delivery and programming.",
                                        "url": "https://qilifestore.com/products/qi-coil-mini-system-with-rc1",
                                        "keywords": [
                                        "frequency therapy",
                                        "qi coil",
                                        "resonant console",
                                        "energy balancing",
                                        "wellness",
                                        "health",
                                        "productivité",
                                        "efficacité",
                                        "temps",
                                        "travail"
                                        ]
                                    },
                                    "product3": {
                                        "name": "Qi Coil 3S Transformation System",
                                        "description": "Advanced three-coil system designed for whole-body frequency application and deep energetic transformation.",
                                        "url": "https://qilifestore.com/products/qi-coil-3s-transformation-system",
                                        "keywords": [
                                        "transformation",
                                        "frequency system",
                                        "multiple coils",
                                        "3S",
                                        "energy medicine",
                                        "whole-body therapy",
                                        "deep energetic work",
                                        "chronic conditions",
                                        "energy blockages",
                                        "recovery support",
                                        "vitality enhancement"
                                        ]
                                    },
                                    "product4": {
                                        "name": "Qi Coil Max Scalar Pro RC2",
                                        "description": "Professional-grade scalar wave frequency system with enhanced power and the advanced Resonant Console 2 for maximum therapeutic potential.",
                                        "keywords": [
                                        "scalar waves",
                                        "professional system",
                                        "max power",
                                        "RC2",
                                        "resonant console",
                                        "advanced frequency therapy",
                                        "therapeutic applications",
                                        "complex health",
                                        "chronic conditions",
                                        "deep energy imbalances"
                                        ],
                                        "url": "https://qilifestore.com/collections/qi-coils/products/qi-coil-max-scalar-pro-rc2"
                                    },
                                    "product5": {
                                        "name": "Resonant Console",
                                        "description": "Core frequency programming console for Qi Coil systems, offering fundamental frequency capabilities and user-friendly operation.",
                                        "keywords": [
                                        "frequency console",
                                        "programming device",
                                        "qi coil compatible",
                                        "core library",
                                        "user-friendly",
                                        "basic applications",
                                        "beginner therapy",
                                        "stress management",
                                        "sleep support",
                                        "everyday vitality"
                                        ],
                                        "url": "https://qilifestore.com/collections/qi-coils/products/resonant-console"
                                    },
                                    "product6": {
                                        "name": "Resonant Wave Console 2",
                                        "description": "Advanced second-generation console with expanded frequency capabilities, improved interface, and enhanced programming options for Qi Coil systems.",
                                        "keywords": [
                                        "advanced console",
                                        "wave frequencies",
                                        "expanded library",
                                        "RC2",
                                        "qi coil controller",
                                        "second generation",
                                        "customized therapy",
                                        "targeted wellness",
                                        "intermediate energy work"
                                        ],
                                        "url": "https://qilifestore.com/collections/qi-coils/products/resonant-wave-console-2"
                                    },
                                    "product7": {
                                        "name": "Resonant Console 3 Higher Quantum",
                                        "description": "Premium third-generation console featuring 151,000 frequencies, quantum processing capabilities, and the most advanced programming interface for Qi Coil systems.",
                                        "keywords": [
                                        "quantum frequencies",
                                        "151,000 frequencies",
                                        "RC3",
                                        "professional console",
                                        "advanced technology",
                                        "premium controller",
                                        "energy medicine",
                                        "research",
                                        "intensive therapy",
                                        "complex wellness"
                                        ],
                                        "url": "https://qilifestore.com/collections/qi-coils/products/resonant-console-3-higher-quantum-151-000-frequencies"
                                    },
                                    "product8": {
                                        "name": "Resonant Console Advanced",
                                        "description": "Specialized advanced console with premium features, enhanced processing power, and exclusive frequency sets for professional and therapeutic applications.",
                                        "keywords": [
                                        "premium console",
                                        "exclusive frequencies",
                                        "professional grade",
                                        "advanced controller",
                                        "specialized applications",
                                        "enhanced processing",
                                        "research",
                                        "therapeutic"
                                        ],
                                        "url": "https://qilifestore.com/collections/qi-coils/products/resonant-console-advanced"
                                    },
                                    "product9": {
                                        "name": "Resonant Console 4 Inner Circle",
                                        "description": "Elite fourth-generation console with exclusive inner circle access, cutting-edge frequency technology, and the most comprehensive programming capabilities available.",
                                        "keywords": [
                                        "inner circle",
                                        "RC4",
                                        "elite console",
                                        "exclusive technology",
                                        "premium controller",
                                        "cutting-edge",
                                        "comprehensive programming",
                                        "advanced research",
                                        "professional systems",
                                        "complex health"
                                        ],
                                        "url": "https://qilifestore.com/collections/qi-coils/products/resonant-console-4-inner-circle"
                                    }
                                    }
                    # Sauvegarder les produits par défaut dans la base de données
                    for product_id, product_data in self.products.items():
                        self.db.save_product(product_id, product_data)
            
            # Charger les personas
            self.personas = self.db.get_all_personas()
            if not self.personas:
                # Si aucun persona n'est trouvé dans la base de données, essayer de les charger depuis le fichier JSON
                if os.path.exists("personas.json"):
                    with open("personas.json", 'r', encoding='utf-8') as f:
                        self.personas = json.load(f)
                        # Sauvegarder les personas dans la base de données
                        for persona_id, persona_data in self.personas.items():
                            self.db.save_persona(persona_id, persona_data)
                else:
                    # Créer des personas par défaut
                    self.personas = {
                        "helpful": {
                            "name": "Health Enthusiast",
                            "tone": "Enthusiastic, supportive, personal",
                            "style": "informative"
                        },
                        "enthusiastic": {
                            "name": "Wellness Professional",
                            "tone": "Informative, authoritative, helpful",
                            "style": "energetic"
                        },
                        "expert": {
                            "name": "Curious Explorer",
                            "tone": "Curious, open-minded, conversationa",
                            "style": "detailed"
                        }              
                    }
                    # Sauvegarder les personas par défaut dans la base de données
                    for persona_id, persona_data in self.personas.items():
                        self.db.save_persona(persona_id, persona_data)
            
            # Charger les templates de commentaires
            self.comment_templates = self.db.get_all_comment_templates()
            if not self.comment_templates:
                # Si aucun template n'est trouvé dans la base de données, essayer de les charger depuis le fichier JSON
                if os.path.exists("comment_templates.json"):
                    with open("comment_templates.json", 'r', encoding='utf-8') as f:
                        self.comment_templates = json.load(f)
                        # Sauvegarder les templates dans la base de données
                        for template_id, content in self.comment_templates.items():
                            self.db.save_comment_template(template_id, content)
                else:
                    self.comment_templates = {
                        
                        "default": "I found a solution to this problem! {product_name} really helped me. You can find it here: {product_url}",
                        "question": "Have you tried {product_name}? It's exactly what you need for this case. Here's the link: {product_url}",
                        "experience": "I had the same problem and {product_name} solved it. I highly recommend it: {product_url}",
                        "solution": "I solved my problem with {product_name}. It's really a powerful tool: {product_url}",
                        "recommendation": "I strongly recommend {product_name} to solve this problem: {product_url}",
                        "testimonial": "I was very satisfied with using {product_name}. It's exactly what I needed: {product_url}",
                        "comparison": "I compared {product_name} with other products and it's the best: {product_url}",
                        "alternative": "If you can't use {product_name}, you can try {alternative_product_name}: {alternative_product_url}"
                    }
                    # Sauvegarder les templates par défaut dans la base de données
                    for template_id, content in self.comment_templates.items():
                        self.db.save_comment_template(template_id, content)
            
            logger.info(f"Produits ({len(self.products)}), personas ({len(self.personas)}) et templates ({len(self.comment_templates)}) chargés")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des produits et personas: {e}")
            self.products = {}
            self.personas = {}
            self.comment_templates = {}
    
    def _setup_scheduler(self):
        """Configure le planificateur pour les tâches récurrentes."""
        # Réinitialiser le compteur de commentaires quotidien à minuit
        schedule.every().day.at("00:00").do(self._reset_daily_counter)
        
        # Sauvegarder les statistiques quotidiennes
        schedule.every().day.at("23:59").do(self._save_daily_stats)
        
        logger.info("Planificateur configuré")
    
    def _reset_daily_counter(self):
        """Réinitialise le compteur de commentaires quotidien."""
        self.comments_posted_today = 0
        self.posts_analyzed = 0
        self.posts_filtered = 0
        self.posts_selected = 0
        logger.info("Compteur de commentaires quotidien réinitialisé")
    
    def _save_daily_stats(self):
        """Sauvegarde les statistiques quotidiennes."""
        stats = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "comments_posted": self.comments_posted_today,
            "posts_analyzed": self.posts_analyzed,
            "posts_filtered": self.posts_filtered,
            "posts_selected": self.posts_selected
        }
        logger.info(f"Statistiques quotidiennes: {stats}")
        
        # Dans une version réelle, on sauvegarderait les statistiques dans la base de données
        try:
            self.db.save_stats(stats)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des statistiques: {e}")
    
    def _is_active_hour(self) -> bool:
        """Vérifie si l'heure actuelle est dans la plage d'heures actives."""
        current_hour = datetime.datetime.now().hour
        return self.active_hours_start <= current_hour < self.active_hours_end
    
    def _filter_post(self, post) -> Dict[str, Any]:
        """
        Filtre les publications selon les critères définis.
        
        Args:
            post: Publication Reddit à filtrer
            
        Returns:
            Dict[str, Any]: Résultat du filtrage avec raison si rejeté
        """
        logger.debug(f"Filtrage de la publication {post.id}: titre='{post.title[:50]}...'")
        result = {
            "passed": True,
            "reason": None
        }
        
        # Vérifier le score
        if post.score < self.min_post_score:
            result["passed"] = False
            result["reason"] = f"Score trop bas: {post.score} < {self.min_post_score}"
            logger.debug(f"Publication {post.id} rejetée: {result['reason']}")
            return result
        
        # Vérifier l'âge
        post_age_hours = (time.time() - post.created_utc) / 3600
        if post_age_hours > self.max_post_age_hours:
            result["passed"] = False
            result["reason"] = f"Publication trop ancienne: {post_age_hours:.1f}h > {self.max_post_age_hours}h"
            logger.debug(f"Publication {post.id} rejetée: {result['reason']}")
            return result
        
        # Vérifier les mots-clés interdits
        post_content = f"{post.title} {post.selftext}".lower()
        for keyword in self.forbidden_keywords:
            if keyword.lower() in post_content:
                result["passed"] = False
                result["reason"] = f"Contient un mot-clé interdit: {keyword}"
                logger.debug(f"Publication {post.id} rejetée: {result['reason']}")
                return result
        
        # Vérifier si le post est NSFW
        if post.over_18:
            result["passed"] = False
            result["reason"] = "Publication marquée NSFW"
            logger.debug(f"Publication {post.id} rejetée: {result['reason']}")
            return result
        
        logger.debug(f"Publication {post.id} a passé tous les filtres")
        return result
    
    def _select_product_for_post(self, post) -> Optional[Dict]:
        """
        Sélectionne un produit pertinent pour la publication.
        
        Args:
            post: Publication Reddit
            
        Returns:
            Optional[Dict]: Produit sélectionné ou None si aucun produit pertinent
        """
        logger.debug(f"Sélection d'un produit pour la publication {post.id}")
        if not self.products:
            logger.warning("Aucun produit disponible pour la sélection")
            return None
        
        # Combiner le titre et le texte de la publication
        post_content = f"{post.title} {post.selftext}".lower()
        logger.debug(f"Contenu analysé de la publication {post.id}: '{post_content[:100]}...'")
        
        # Calculer la pertinence de chaque produit
        product_scores = {}
        for product_id, product in self.products.items():
            score = 0
            keywords = product.get("keywords", [])
            
            logger.debug(f"Évaluation du produit {product['name']} (id: {product_id}) pour la publication {post.id}")
            logger.debug(f"Mots-clés du produit: {keywords}")
            
            keyword_matches = []
            for keyword in keywords:
                if keyword.lower() in post_content:
                    score += 1
                    keyword_matches.append(keyword)
            
            if score > 0:
                product_scores[product_id] = score
                logger.debug(f"Produit {product['name']} a un score de {score}. Mots-clés trouvés: {keyword_matches}")
            else:
                logger.debug(f"Produit {product['name']} n'a pas de correspondance pour cette publication")
        
        # Sélectionner le produit le plus pertinent
        if product_scores:
            best_product_id = max(product_scores, key=product_scores.get)
            best_score = product_scores[best_product_id]
            selected_product = {
                "id": best_product_id,
                "score": best_score,
                **self.products[best_product_id]
            }
            logger.info(f"Produit sélectionné pour la publication {post.id}: {selected_product['name']} (score: {best_score})")
            return selected_product
        
        logger.info(f"Aucun produit pertinent trouvé pour la publication {post.id}")
        return None
    
    def _select_persona(self) -> Dict:
        """
        Sélectionne un persona aléatoire.
        
        Returns:
            Dict: Persona sélectionné
        """
        if not self.personas:
            default_persona = {
                "name": "Assistant",
                "tone": "helpful",
                "style": "informative"
            }
            logger.warning(f"Aucun persona disponible, utilisation du persona par défaut: {default_persona['name']}")
            return default_persona
        
        persona_id = random.choice(list(self.personas.keys()))
        selected_persona = {
            "id": persona_id,
            **self.personas[persona_id]
        }
        logger.info(f"Persona sélectionné: {selected_persona['name']}")
        return selected_persona
    
    def _generate_comment(self, post, product: Dict, persona: Dict) -> str:
        """
        Génère un commentaire pour la publication en utilisant OpenAI.
        
        Args:
            post: Publication Reddit
            product: Produit à promouvoir
            persona: Persona à utiliser
            
        Returns:
            str: Commentaire généré
        """
        try:
            logger.debug(f"Début de génération de commentaire pour la publication {post.id}")
            logger.debug(f"Utilisant le produit: {product['name']} et le persona: {persona['name']}")
            
            if not self.openai_model or not self.openai_client:
                logger.debug("OpenAI non configuré, utilisation d'un template prédéfini")
                # Si OpenAI n'est pas configuré, utiliser un template prédéfini
                template_id = random.choice(list(self.comment_templates.keys()))
                template = self.comment_templates[template_id]
                logger.debug(f"Template sélectionné: {template_id} - '{template}'")
                comment = template.format(
                    product_name=product["name"],
                    product_url=product["url"]
                )
                logger.info(f"Commentaire généré avec template {template_id}: {comment[:50]}...")
                return comment
            
            # Génération d'un commentaire avec OpenAI
            logger.debug(f"Préparation du prompt OpenAI pour la publication {post.id}")
            prompt = f"""
            You are a marketing assistant who responds to Reddit posts.
            
            Post:
            Title: {post.title}
            Content: {post.selftext}
            
            Product to promote:
            Name: {product["name"]}
            Description: {product["description"]}
            URL: {product["url"]}
            
            Your persona:
            Name: {persona["name"]}
            Tone: {persona["tone"]}
            Style: {persona["style"]}
            
            Write a Reddit comment that:
            1. Is relevant to the post
            2. Subtly mentions the product as a solution
            3. Includes the product URL
            4. Uses the tone and style of the persona
            5. Is natural and doesn't look like obvious advertising
            6. Is concise (maximum 3 sentences)
            
            Comment:
            """
            
            logger.info(f"Génération de commentaire avec OpenAI pour la publication {post.id}")
            logger.debug(f"Appel API OpenAI avec modèle: {self.openai_model}")
            
            # Utiliser la nouvelle API OpenAI (v1.0.0+)
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a marketing assistant who helps write Reddit comments."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            comment = response.choices[0].message.content.strip()
            logger.info(f"Commentaire généré avec OpenAI: {comment[:50]}...")
            logger.debug(f"Commentaire complet: {comment}")
            return comment
        except Exception as e:
            logger.error(f"Erreur lors de la génération du commentaire avec OpenAI: {e}")
            logger.debug(f"Détails de l'erreur pour la publication {post.id}: {str(e)}", exc_info=True)
            
            # En cas d'erreur, utiliser un template prédéfini
            template_id = random.choice(list(self.comment_templates.keys()))
            template = self.comment_templates[template_id]
            comment = template.format(
                product_name=product["name"],
                product_url=product["url"]
            )
            logger.info(f"Fallback sur template {template_id} après erreur: {comment[:50]}...")
            return comment
    
    def _post_comment(self, post, comment: str) -> bool:
        """
        Poste un commentaire sur la publication.
        
        Args:
            post: Publication Reddit
            comment: Commentaire à poster
            
        Returns:
            bool: True si le commentaire a été posté avec succès, False sinon
        """
        try:
            logger.debug(f"Tentative de publication d'un commentaire sur {post.id}")
            logger.debug(f"Commentaire à poster: '{comment}'")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Commentaire qui serait posté sur {post.id}: {comment}")
                return True
            
            if not self.reddit:
                logger.warning("Client Reddit non initialisé, impossible de poster le commentaire")
                return False
            
            # Poster le commentaire
            logger.debug(f"Envoi du commentaire à l'API Reddit pour la publication {post.id}")
            comment_response = post.reply(comment)
            
            logger.info(f"Commentaire posté avec succès sur {post.id}, ID du commentaire: {comment_response.id}")
            logger.debug(f"URL du commentaire posté: https://www.reddit.com{comment_response.permalink}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la publication du commentaire: {e}")
            logger.debug(f"Détails de l'erreur pour la publication {post.id}: {str(e)}", exc_info=True)
            return False
    
    def monitor_subreddits(self) -> Dict[str, Any]:
        """
        Surveille les subreddits et poste des commentaires si nécessaire.
        
        Returns:
            Dict[str, Any]: Statistiques du cycle de surveillance
        """
        if not self.reddit:
            logger.warning("Client Reddit non initialisé, impossible de surveiller les subreddits")
            return {"error": "Client Reddit non initialisé", "comments_posted": 0}
        
        stats = {
            "subreddits_checked": 0,
            "posts_analyzed": 0,
            "posts_filtered": 0,
            "posts_selected": 0,
            "comments_posted": 0,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        logger.debug(f"Début d'un cycle de surveillance avec subreddits cibles: {self.subreddits}")
        
        # Vérifier si le bot est actif et si l'heure actuelle est dans la plage d'heures actives
        if not self.active:
            logger.info("Bot inactif, surveillance ignorée")
            return stats
        
        if not self._is_active_hour():
            current_hour = datetime.datetime.now().hour
            logger.info(f"Heure inactive ({current_hour}h), surveillance ignorée. Plage active: {self.active_hours_start}h-{self.active_hours_end}h")
            return stats
        
        try:
            # Parcourir chaque subreddit
            for subreddit_name in self.subreddits:
                try:
                    logger.info(f"Surveillance du subreddit: r/{subreddit_name}")
                    subreddit = self.reddit.subreddit(subreddit_name)
                    stats["subreddits_checked"] += 1
                    
                    logger.debug(f"Récupération des {20} publications récentes de r/{subreddit_name}")
                    # Parcourir les publications récentes
                    for post in subreddit.new(limit=20):
                        stats["posts_analyzed"] += 1
                        self.posts_analyzed += 1
                        
                        # Log détaillé de la publication
                        logger.info(f"Analyse de la publication {post.id} de r/{subreddit_name}: '{post.title[:50]}...'")
                        
                        # Log complet du contenu de la publication
                        logger.info(f"QUESTION r/{subreddit_name} - {post.id} - TITRE COMPLET: {post.title}")
                        logger.info(f"QUESTION r/{subreddit_name} - {post.id} - AUTEUR: u/{post.author.name if post.author else '[deleted]'}")
                        logger.info(f"QUESTION r/{subreddit_name} - {post.id} - URL: https://www.reddit.com{post.permalink}")
                        
                        # Log le contenu texte complet de la publication
                        if hasattr(post, 'selftext') and post.selftext:
                            # Tronquer si très long, mais conserver le début et la fin
                            if len(post.selftext) > 1000:
                                selftext_preview = f"{post.selftext[:500]}...\n[CONTENU TRONQUÉ - {len(post.selftext)} caractères]...\n{post.selftext[-500:]}"
                            else:
                                selftext_preview = post.selftext
                            logger.info(f"QUESTION r/{subreddit_name} - {post.id} - CONTENU:\n{selftext_preview}")
                        else:
                            logger.info(f"QUESTION r/{subreddit_name} - {post.id} - CONTENU: [Pas de texte, lien externe]")
                            if hasattr(post, 'url'):
                                logger.info(f"QUESTION r/{subreddit_name} - {post.id} - LIEN: {post.url}")
                        
                        logger.debug(f"Publication {post.id} - Score: {post.score}, Âge: {(time.time() - post.created_utc) / 3600:.1f}h, NSFW: {post.over_18}")
                        
                        # Filtrer les publications
                        filter_result = self._filter_post(post)
                        if not filter_result["passed"]:
                            stats["posts_filtered"] += 1
                            self.posts_filtered += 1
                            logger.info(f"Publication {post.id} filtrée: {filter_result['reason']}")
                            continue
                        
                        logger.info(f"Publication {post.id} a passé les filtres")
                        
                        # Sélectionner un produit pertinent
                        product = self._select_product_for_post(post)
                        if not product:
                            logger.info(f"Aucun produit pertinent pour la publication {post.id}")
                            continue
                        
                        stats["posts_selected"] += 1
                        self.posts_selected += 1
                        
                        # Sélectionner un persona
                        persona = self._select_persona()
                        logger.debug(f"Persona sélectionné pour la publication {post.id}: {persona['name']} (tone: {persona['tone']}, style: {persona['style']})")
                        
                        # Générer un commentaire
                        comment = self._generate_comment(post, product, persona)
                        
                        # Poster le commentaire
                        if self._post_comment(post, comment):
                            stats["comments_posted"] += 1
                            self.comments_posted_today += 1
                            self.total_comments_posted += 1
                            self.last_comment_time = int(time.time())
                            
                            # Attendre le délai entre les commentaires
                            logger.info(f"Attente de {self.comment_rate_limit_seconds} secondes avant le prochain commentaire")
                            time.sleep(self.comment_rate_limit_seconds)
                except Exception as e:
                    logger.error(f"Erreur lors de la surveillance du subreddit {subreddit_name}: {e}")
                    logger.debug(f"Détails de l'erreur pour le subreddit {subreddit_name}: {str(e)}", exc_info=True)
        except Exception as e:
            logger.error(f"Erreur lors de la surveillance des subreddits: {e}")
            logger.debug(f"Détails de l'erreur générale: {str(e)}", exc_info=True)
        
        # Log des statistiques du cycle
        logger.info(f"Cycle de surveillance terminé: {stats}")
        return stats
    
    def reload_credentials(self):
        """Recharge les identifiants depuis la base de données."""
        self._init_reddit_client()
        self._init_openai_client()
        logger.info("Identifiants rechargés depuis la base de données")
    
    def reload_config(self):
        """Recharge la configuration depuis la base de données."""
        logger.info("Rechargement de la configuration en cours...")
        self._load_config_from_db()
        self._load_products_and_personas()
        logger.info("Configuration rechargée depuis la base de données")
        logger.info("Paramètres actuels du bot:")
        logger.info(f"Subreddits: {self.subreddits}")
        logger.info(f"Heures actives: {self.active_hours_start}h-{self.active_hours_end}h")
        logger.info(f"Score minimum: {self.min_post_score}")
        logger.info(f"Âge maximum: {self.max_post_age_hours} heures")
        logger.info(f"Délai entre commentaires: {self.comment_rate_limit_seconds} secondes")
        logger.info(f"Mode dry-run: {self.dry_run}")
        logger.info(f"Mots-clés interdits: {self.forbidden_keywords}")
        logger.info(f"Langues exclues: {self.excluded_languages}")
