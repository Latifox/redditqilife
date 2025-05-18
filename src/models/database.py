"""
Module de gestion de la base de données pour le bot Reddit.
"""
import os
import json
import sqlite3
from typing import Dict, Any, Optional
import logging

# Configuration du logging
logger = logging.getLogger("RedditBotDB")

class Database:
    """Classe pour gérer la base de données du bot Reddit."""
    
    def __init__(self, db_path: str = "reddit_bot.db"):
        """
        Initialise la connexion à la base de données.
        
        Args:
            db_path: Chemin vers le fichier de base de données SQLite
        """
        self.db_path = db_path
        self._create_tables()
    
    def _get_connection(self):
        """Établit une connexion à la base de données."""
        return sqlite3.connect(self.db_path)
    
    def _create_tables(self):
        """Crée les tables nécessaires si elles n'existent pas."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Table pour les identifiants Reddit et OpenAI
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Table pour les configurations générales
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Table pour les produits
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                product_id TEXT UNIQUE,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Table pour les personas
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY,
                persona_id TEXT UNIQUE,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Table pour les templates de commentaires
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_templates (
                id INTEGER PRIMARY KEY,
                template_id TEXT UNIQUE,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Tables de base de données créées avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la création des tables: {e}")
            raise
    
    def save_credential(self, name: str, value: str) -> bool:
        """
        Sauvegarde ou met à jour un identifiant.
        
        Args:
            name: Nom de l'identifiant (ex: 'reddit_username', 'openai_api_key')
            value: Valeur de l'identifiant
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Vérifier si l'identifiant existe déjà
            cursor.execute("SELECT id FROM credentials WHERE name = ?", (name,))
            result = cursor.fetchone()
            
            if result:
                # Mise à jour
                cursor.execute(
                    "UPDATE credentials SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                    (value, name)
                )
            else:
                # Insertion
                cursor.execute(
                    "INSERT INTO credentials (name, value) VALUES (?, ?)",
                    (name, value)
                )
            
            conn.commit()
            conn.close()
            logger.info(f"Identifiant '{name}' sauvegardé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'identifiant '{name}': {e}")
            return False
    
    def get_credential(self, name: str) -> Optional[str]:
        """
        Récupère un identifiant par son nom.
        
        Args:
            name: Nom de l'identifiant
            
        Returns:
            Optional[str]: Valeur de l'identifiant ou None si non trouvé
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM credentials WHERE name = ?", (name,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'identifiant '{name}': {e}")
            return None
    
    def get_all_credentials(self) -> Dict[str, str]:
        """
        Récupère tous les identifiants.
        
        Returns:
            Dict[str, str]: Dictionnaire des identifiants {nom: valeur}
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, value FROM credentials")
            results = cursor.fetchall()
            
            conn.close()
            
            return {name: value for name, value in results}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des identifiants: {e}")
            return {}
    
    def delete_credential(self, name: str) -> bool:
        """
        Supprime un identifiant.
        
        Args:
            name: Nom de l'identifiant
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM credentials WHERE name = ?", (name,))
            conn.commit()
            conn.close()
            
            logger.info(f"Identifiant '{name}' supprimé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'identifiant '{name}': {e}")
            return False
    
    def save_config(self, name: str, value: Any) -> bool:
        """
        Sauvegarde ou met à jour une configuration.
        
        Args:
            name: Nom de la configuration
            value: Valeur de la configuration (sera convertie en JSON)
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            # Conversion en JSON si nécessaire
            if not isinstance(value, str):
                value = json.dumps(value)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Vérifier si la configuration existe déjà
            cursor.execute("SELECT id FROM config WHERE name = ?", (name,))
            result = cursor.fetchone()
            
            if result:
                # Mise à jour
                cursor.execute(
                    "UPDATE config SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                    (value, name)
                )
            else:
                # Insertion
                cursor.execute(
                    "INSERT INTO config (name, value) VALUES (?, ?)",
                    (name, value)
                )
            
            conn.commit()
            conn.close()
            logger.info(f"Configuration '{name}' sauvegardée avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration '{name}': {e}")
            return False
    
    def get_config(self, name: str, default: Any = None) -> Any:
        """
        Récupère une configuration par son nom.
        
        Args:
            name: Nom de la configuration
            default: Valeur par défaut si non trouvée
            
        Returns:
            Any: Valeur de la configuration (convertie depuis JSON si possible)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM config WHERE name = ?", (name,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                value = result[0]
                # Essayer de convertir depuis JSON
                try:
                    return json.loads(value)
                except:
                    return value
            return default
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la configuration '{name}': {e}")
            return default
    
    def save_product(self, product_id: str, data: Dict) -> bool:
        """
        Sauvegarde ou met à jour un produit.
        
        Args:
            product_id: Identifiant du produit
            data: Données du produit
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            json_data = json.dumps(data)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Vérifier si le produit existe déjà
            cursor.execute("SELECT id FROM products WHERE product_id = ?", (product_id,))
            result = cursor.fetchone()
            
            if result:
                # Mise à jour
                cursor.execute(
                    "UPDATE products SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?",
                    (json_data, product_id)
                )
            else:
                # Insertion
                cursor.execute(
                    "INSERT INTO products (product_id, data) VALUES (?, ?)",
                    (product_id, json_data)
                )
            
            conn.commit()
            conn.close()
            logger.info(f"Produit '{product_id}' sauvegardé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du produit '{product_id}': {e}")
            return False
    
    def get_all_products(self) -> Dict[str, Dict]:
        """
        Récupère tous les produits.
        
        Returns:
            Dict[str, Dict]: Dictionnaire des produits {id: données}
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT product_id, data FROM products")
            results = cursor.fetchall()
            
            conn.close()
            
            products = {}
            for product_id, data in results:
                try:
                    products[product_id] = json.loads(data)
                except:
                    logger.warning(f"Impossible de parser les données du produit '{product_id}'")
            
            return products
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des produits: {e}")
            return {}
    
    def save_persona(self, persona_id: str, data: Dict) -> bool:
        """
        Sauvegarde ou met à jour un persona.
        
        Args:
            persona_id: Identifiant du persona
            data: Données du persona
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            json_data = json.dumps(data)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Vérifier si le persona existe déjà
            cursor.execute("SELECT id FROM personas WHERE persona_id = ?", (persona_id,))
            result = cursor.fetchone()
            
            if result:
                # Mise à jour
                cursor.execute(
                    "UPDATE personas SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE persona_id = ?",
                    (json_data, persona_id)
                )
            else:
                # Insertion
                cursor.execute(
                    "INSERT INTO personas (persona_id, data) VALUES (?, ?)",
                    (persona_id, json_data)
                )
            
            conn.commit()
            conn.close()
            logger.info(f"Persona '{persona_id}' sauvegardé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du persona '{persona_id}': {e}")
            return False
    
    def get_all_personas(self) -> Dict[str, Dict]:
        """
        Récupère tous les personas.
        
        Returns:
            Dict[str, Dict]: Dictionnaire des personas {id: données}
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT persona_id, data FROM personas")
            results = cursor.fetchall()
            
            conn.close()
            
            personas = {}
            for persona_id, data in results:
                try:
                    personas[persona_id] = json.loads(data)
                except:
                    logger.warning(f"Impossible de parser les données du persona '{persona_id}'")
            
            return personas
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des personas: {e}")
            return {}
    
    def save_comment_template(self, template_id: str, content: str) -> bool:
        """
        Sauvegarde ou met à jour un template de commentaire.
        
        Args:
            template_id: Identifiant du template
            content: Contenu du template
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Vérifier si le template existe déjà
            cursor.execute("SELECT id FROM comment_templates WHERE template_id = ?", (template_id,))
            result = cursor.fetchone()
            
            if result:
                # Mise à jour
                cursor.execute(
                    "UPDATE comment_templates SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE template_id = ?",
                    (content, template_id)
                )
            else:
                # Insertion
                cursor.execute(
                    "INSERT INTO comment_templates (template_id, content) VALUES (?, ?)",
                    (template_id, content)
                )
            
            conn.commit()
            conn.close()
            logger.info(f"Template de commentaire '{template_id}' sauvegardé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du template de commentaire '{template_id}': {e}")
            return False
    
    def get_all_comment_templates(self) -> Dict[str, str]:
        """
        Récupère tous les templates de commentaires.
        
        Returns:
            Dict[str, str]: Dictionnaire des templates {id: contenu}
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT template_id, content FROM comment_templates")
            results = cursor.fetchall()
            
            conn.close()
            
            return {template_id: content for template_id, content in results}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des templates de commentaires: {e}")
            return {}
    
    def import_from_json_files(self) -> bool:
        """
        Importe les données depuis les fichiers JSON existants.
        
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            # Importation des produits
            if os.path.exists("products.json"):
                with open("products.json", 'r', encoding='utf-8') as f:
                    products = json.load(f)
                    for product_id, data in products.items():
                        self.save_product(product_id, data)
            
            # Importation des personas
            if os.path.exists("personas.json"):
                with open("personas.json", 'r', encoding='utf-8') as f:
                    personas = json.load(f)
                    for persona_id, data in personas.items():
                        self.save_persona(persona_id, data)
            
            # Importation des templates de commentaires
            if os.path.exists("comment_templates.json"):
                with open("comment_templates.json", 'r', encoding='utf-8') as f:
                    templates = json.load(f)
                    for template_id, content in templates.items():
                        self.save_comment_template(template_id, content)
            
            # Importation des identifiants depuis .env
            if os.path.exists(".env"):
                with open(".env", 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key and value:
                                self.save_credential(key.lower(), value)
            
            logger.info("Importation des données depuis les fichiers JSON réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'importation des données depuis les fichiers JSON: {e}")
            return False
    
    def export_to_json_files(self) -> bool:
        """
        Exporte les données vers des fichiers JSON.
        
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            # Exportation des produits
            products = self.get_all_products()
            with open("products.json", 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            
            # Exportation des personas
            personas = self.get_all_personas()
            with open("personas.json", 'w', encoding='utf-8') as f:
                json.dump(personas, f, indent=2, ensure_ascii=False)
            
            # Exportation des templates de commentaires
            templates = self.get_all_comment_templates()
            with open("comment_templates.json", 'w', encoding='utf-8') as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
            
            # Exportation des identifiants vers .env
            credentials = self.get_all_credentials()
            with open(".env.export", 'w', encoding='utf-8') as f:
                for key, value in credentials.items():
                    f.write(f"{key.upper()}={value}\n")
            
            logger.info("Exportation des données vers les fichiers JSON réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'exportation des données vers les fichiers JSON: {e}")
            return False
