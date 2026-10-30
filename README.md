# Kibare - L'information en toute confiance

**Une messagerie sécurisée, souveraine et adaptée aux besoins des institutions burkinabè.**

Kibare est un prototype de messagerie instantanée développé dans le cadre du Sprint Technique Pré-Hackathon 2026 (Hackathon 226 - Édition 2026).

Le projet explore la mise en place d'une solution de communication institutionnelle reposant sur des technologies ouvertes, une infrastructure auto-hébergeable et les mécanismes de chiffrement de bout en bout proposés par Matrix.

## Stack technique

- **Matrix Synapse** - Serveur de communication.
- **Element Web** - Client de messagerie.
- **PostgreSQL** - Système de gestion de base de données.
- **Docker Compose** - Orchestration des services.

*Caddy, pour le reverse proxy et la gestion TLS, est envisagé pour un futur déploiement, mais n'est pas encore intégré.*

## Prérequis

- Git.
- Docker installé et fonctionnel.
- Docker Compose (plugin `docker compose`).
- OpenSSL.
- Bash.

## Installation et démarrage

Récupérer le projet :

```bash
git clone https://github.com/only-for-geek/Kibare.git
cd Kibare
```

Rendre le script exécutable :

```bash
chmod +x start.sh
```

Lancer Kibare :

```bash
./start.sh
```

Le script automatise plusieurs opérations :

- Vérification des prérequis.
- Création du fichier `.env` et génération d'un secret PostgreSQL si nécessaire.
- Initialisation de la configuration Synapse lorsqu'elle est absente.
- Vérification de la cohérence de la configuration PostgreSQL.
- Validation de la configuration Synapse.
- Démarrage des services Docker Compose.

Les configurations et secrets déjà présents sont conservés. Le script s'arrête lorsqu'il détecte une incohérence nécessitant une intervention manuelle.

**État des tests :** le démarrage et la validation d'une installation existante ont été vérifiés. Le parcours complet de première installation reste à tester sur une machine vierge.

## Accès aux services

Une fois les services démarrés :

- **Element Web :** http://127.0.0.1:8080
- **API Matrix :** http://127.0.0.1:8008

Ces adresses sont destinées à un environnement local. Elles ne constituent pas une configuration de déploiement accessible depuis Internet.

## Architecture et sécurité

Kibare utilise Matrix Synapse comme serveur central de communication, PostgreSQL pour la persistance des données et Element Web comme interface utilisateur.

Les ports exposés sont limités à l'interface locale de la machine. Les données persistantes et les secrets sont conservés localement et exclus du dépôt Git.

Le chiffrement de bout en bout dépend de son activation dans les salons Matrix. La configuration actuelle constitue un prototype local et ne doit pas être considérée comme une infrastructure de production auditée.

## Objectifs

- Faciliter les communications institutionnelles sécurisées.
- Favoriser la maîtrise de l'infrastructure par l'organisation qui l'héberge.
- S'appuyer sur un protocole ouvert et interopérable.
- Explorer la gestion des identités, des accès et des révocations de sessions.

## État du projet

Kibare est actuellement au stade de prototype technique.

Les composants principaux - Synapse, PostgreSQL et Element Web - sont configurés et orchestrés avec Docker Compose.

Plusieurs fonctionnalités restent à développer ou à valider, notamment :

- Gestion avancée des identités et des rôles.
- Gestion des accès et révocation des sessions.
- Déploiement HTTPS avec nom de domaine.
- Supervision et journalisation.
- Sauvegarde et restauration des données.
- Audit de sécurité.

## Documentation

Le dossier `docs/` contient :

- `architecture.md` - Présentation de l'architecture technique.
- `security.md` - Mesures de sécurité et limites actuelles.
- `progress.md` - État d'avancement du projet.

D'autres guides sont disponibles :

- `synapse/README` - Guide de configuration du serveur Matrix.
- `tests/README` - Procédures de vérification et de test.

## Contribution

Les retours, tests et contributions des membres de l'équipe sont les bienvenus.

Avant toute modification, vérifier les consignes de configuration et de sécurité présentes dans la documentation.

## Licence

La licence du projet reste à définir. Le fichier `LICENSE` sera ajouté après validation du choix de licence.