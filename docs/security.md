# Sécurité de Kibare

## 1. Objectif

La sécurité est un principe fondamental du projet Kibare. La plateforme s'appuie sur le protocole Matrix et sur une infrastructure auto-hébergeable afin de favoriser la maîtrise des communications et des données par l'organisation qui l'exploite.

Ce document présente les mesures de sécurité actuellement mises en place, les limites connues du prototype et les améliorations nécessaires avant un déploiement institutionnel.

## 2. Mesures de sécurité actuelles

### 2.1. Protection des informations sensibles

Les informations de configuration sensibles ne doivent pas être versionnées dans Git.

Les dispositions actuelles comprennent :

- Utilisation d'un fichier `.env` pour stocker le mot de passe PostgreSQL.
- Présence d'un fichier `.env.example` contenant uniquement une valeur indicative.
- Exclusion de `.env` et des données générées par Synapse dans `.gitignore`.

Le fichier `.env` doit rester confidentiel et ne jamais être publié dans le dépôt.

### 2.2. Isolation des services

Les services sont exécutés dans des conteneurs Docker distincts.

La configuration actuelle applique les principes suivants :

- PostgreSQL n'expose aucun port directement sur l'hôte.
- Synapse est accessible localement sur `127.0.0.1:8008`.
- Element Web est accessible localement sur `127.0.0.1:8080`.
- La communication entre Synapse et PostgreSQL s'effectue sur le réseau interne Docker.

Cette configuration limite l'exposition réseau du prototype sur la machine hôte.

### 2.3. Authentification et chiffrement

Synapse fournit les mécanismes d'authentification et de gestion des sessions définis par Matrix.

Matrix prend également en charge le chiffrement de bout en bout dans les salons compatibles lorsque celui-ci est activé.

La présence de ces mécanismes ne constitue toutefois pas, à elle seule, une validation complète de la sécurité de Kibare. Leur configuration et leur fonctionnement doivent être vérifiés par des tests spécifiques.

## 3. Limites actuelles

Kibare est encore un prototype technique destiné à un environnement local.

Les points suivants restent à examiner ou à renforcer :

- Absence de configuration de production avec HTTPS.
- Absence de reverse proxy intégré à la configuration actuelle.
- Politique de sauvegarde et de restauration à définir et à tester.
- Gestion avancée des rôles et des autorisations à développer.
- Procédures de révocation des sessions et de gestion des appareils à valider.
- Audit de sécurité global non encore réalisé.

## 4. Recommandations avant un déploiement institutionnel

Avant toute mise en production, les mesures suivantes devront être étudiées et mises en œuvre :

### 4.1. Sécurité réseau et transport

- Déployer un nom de domaine adapté.
- Activer HTTPS avec des certificats TLS valides.
- Mettre en place un reverse proxy correctement configuré.
- Limiter l'exposition des ports et des services au strict nécessaire.
- Définir les règles de pare-feu adaptées à l'infrastructure.

### 4.2. Gestion des identités et des accès

- Définir une politique de création et de gestion des comptes.
- Mettre en place une gestion cohérente des rôles et des permissions.
- Définir les procédures de désactivation des comptes et de révocation des sessions.
- Examiner la possibilité d'intégrer une authentification renforcée selon les besoins institutionnels.

### 4.3. Protection et continuité des données

- Mettre en place des sauvegardes régulières de PostgreSQL et des données nécessaires à Synapse.
- Protéger les sauvegardes contre les accès non autorisés.
- Tester régulièrement les procédures de restauration.
- Définir une politique de conservation des données.

### 4.4. Supervision et maintenance

- Surveiller l'état des services et les journaux.
- Appliquer régulièrement les mises à jour de sécurité.
- Épingler et contrôler les versions des images Docker.
- Réaliser des audits et des tests de sécurité périodiques.

## 5. Positionnement en matière de sécurité

Kibare adopte une approche de sécurité progressive : les mesures déjà présentes dans le prototype constituent une base technique, mais ne suffisent pas à garantir un niveau de sécurité adapté à une exploitation institutionnelle.

Toute mise en production devra être précédée d'une analyse des risques, de tests techniques et d'une validation des mécanismes de protection.