# Application d'Automatisation Reddit

Cette application permet d'automatiser la surveillance des subreddits, le filtrage des publications pertinentes, et la publication de commentaires promotionnels pour vos produits.

[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/latifox/redditqilife/tree/main)

## Fonctionnalités

- **Surveillance automatique** de subreddits configurables
- **Filtrage intelligent** des publications selon divers critères
- **Génération de commentaires** avec OpenAI adaptés au contexte
- **Personnalisation des personas** pour varier le ton des commentaires
- **Dashboard web** pour le monitoring et la configuration
- **Gestion des identifiants** directement via l'interface web
- **Stockage sécurisé** des identifiants en base de données
- **API REST** pour l'intégration avec d'autres systèmes
- **Mode dry-run** pour tester sans poster réellement
- **Accès sans clé API** - aucune clé API n'est requise pour utiliser l'application

## Installation

### Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Compte développeur Reddit avec identifiants OAuth
- Clé API OpenAI (pour la génération de commentaires)

### Installation des dépendances

```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

## Configuration

### Méthode 1 : Configuration via l'interface web (recommandée)

1. Démarrez l'application
2. Accédez à l'interface web (http://localhost:5000)
3. Allez dans la section "Identifiants" du menu
4. Remplissez les formulaires pour les identifiants Reddit et OpenAI
5. Cliquez sur "Sauvegarder" pour chaque section

### Méthode 2 : Configuration via fichier .env

Créez un fichier `.env` à la racine du projet avec le contenu suivant :

```
# Configuration Reddit
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
EXCLUDED_LANGUAGES=arabic,russian
FORBIDDEN_KEYWORDS=nsfw,politics,religion
```

## Utilisation

### Démarrage de l'application

```bash
cd src
python -m flask --app main run --host=0.0.0.0 --port=5000
```

Accédez ensuite à l'application via `http://localhost:5000`

### Utilisation du dashboard

1. **Tableau de bord** : Visualisez l'état actuel du bot et les statistiques
2. **Identifiants** : Configurez vos identifiants Reddit et OpenAI
3. **Configuration** : Paramétrez les subreddits à surveiller et autres options
4. **Logs** : Consultez les logs d'activité du bot
5. **Statistiques** : Analysez les performances de vos commentaires

### Contrôle du bot

- **Démarrer** : Lance la surveillance automatique des subreddits
- **Arrêter** : Interrompt la surveillance
- **Cycle manuel** : Exécute un cycle de surveillance immédiatement

## Sécurité

- Les identifiants sont stockés de manière sécurisée dans une base de données SQLite
- Les mots de passe et secrets ne sont jamais affichés en clair dans l'interface

## Personnalisation

### Produits

Vous pouvez configurer vos produits dans la section Configuration du dashboard. Chaque produit doit avoir :
- Un nom
- Une description
- Une URL
- Des mots-clés pour la détection de pertinence

### Personas

Les personas permettent de varier le ton des commentaires générés. Configurez-les dans la section Configuration du dashboard.

## API REST

L'API REST est accessible via `/api` et ne nécessite pas de clé API.

Endpoints principaux :
- `GET /api/status` : État actuel du bot
- `POST /api/start` : Démarrer le bot
- `POST /api/stop` : Arrêter le bot
- `POST /api/run` : Exécuter un cycle manuel
- `GET /api/logs` : Récupérer les logs
- `GET /api/config` : Récupérer la configuration
- `POST /api/config` : Mettre à jour la configuration
- `GET /api/credentials` : Récupérer les identifiants (masqués)
- `POST /api/credentials/reddit` : Mettre à jour les identifiants Reddit
- `POST /api/credentials/openai` : Mettre à jour les identifiants OpenAI

## Déploiement

### Avec Docker (Recommandé)

L'application peut facilement être déployée avec Docker :

```bash
# Build et lancer les containers 
docker-compose up -d --build

# Voir les logs
docker-compose logs -f

# Arrêter les containers
docker-compose down
```

### Configuration Docker

Le déploiement Docker inclut :
- Un container web pour l'application Flask
- Un container nginx pour servir l'application et gérer HTTPS
- Un container certbot pour les certificats SSL
- Persistance des données avec volumes Docker

### Avec Gunicorn (Alternative)

Pour un déploiement en production sans Docker, il est recommandé d'utiliser Gunicorn avec un serveur web comme Nginx.

```bash
pip install gunicorn
cd src
gunicorn --bind 0.0.0.0:5000 main:app
```

### Déploiement sur Digital Ocean

Cliquez sur le bouton "Deploy to DO" en haut de ce README pour déployer automatiquement l'application sur Digital Ocean App Platform.

Lors du déploiement, assurez-vous de configurer les variables d'environnement suivantes :
- REDDIT_CLIENT_ID
- REDDIT_CLIENT_SECRET
- REDDIT_USERNAME
- REDDIT_PASSWORD
- REDDIT_USER_AGENT
- OPENAI_API_KEY
- OPENAI_MODEL

## Licence

Ce projet est sous licence MIT.
