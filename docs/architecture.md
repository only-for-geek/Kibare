# Architecture technique de Kibare

## 1. Présentation générale

Kibare est un prototype de plateforme de messagerie instantanée reposant sur le protocole ouvert Matrix. Son architecture s'appuie sur des composants indépendants, conteneurisés avec Docker Compose.

L'objectif est de disposer d'une infrastructure de communication auto-hébergeable, dont l'organisation qui l'exploite conserve la maîtrise.

## 2. Vue d'ensemble

L'architecture actuelle repose sur trois services principaux :

- **Element Web** : interface utilisateur permettant aux utilisateurs d'accéder à la messagerie.
- **Matrix Synapse** : serveur d'accueil Matrix (*homeserver*), responsable de la gestion des utilisateurs, des salons et des échanges de messages.
- **PostgreSQL** : système de gestion de base de données utilisé par Synapse pour la persistance des données.

Docker Compose assure le lancement et l'organisation de ces services.

## 3. Organisation des composants

### 3.1. Client web - Element

Element Web constitue l'interface de communication avec la plateforme.

Il est configuré pour utiliser le serveur Matrix de Kibare :

- Serveur : `kibare.test`
- URL locale : `http://127.0.0.1:8008`
- Configuration : `element/config.json`

Le client est actuellement accessible localement sur le port `8080`.

### 3.2. Serveur Matrix - Synapse

Synapse assure les fonctions centrales de la messagerie :

- Gestion des comptes et des sessions.
- Création et gestion des salons.
- Transmission et synchronisation des événements Matrix.
- Prise en charge des mécanismes de chiffrement de bout en bout proposés par Matrix, lorsque ceux-ci sont activés dans les salons.

Les données et fichiers de configuration générés par Synapse sont conservés dans `synapse/data/`.

### 3.3. Base de données - PostgreSQL

PostgreSQL assure la persistance des données utilisées par Synapse.

La base de données :

- Fonctionne dans un conteneur dédié.
- N'expose pas directement de port sur l'hôte.
- Utilise un volume Docker nommé pour conserver les données.
- Dispose d'un contrôle de santé permettant de vérifier sa disponibilité avant le démarrage de Synapse.

## 4. Flux de communication

Dans la configuration actuelle :

1. L'utilisateur accède à Element Web via son navigateur sur le port `8080`.
2. Element communique avec Synapse via l'API Matrix exposée sur le port `8008`.
3. Synapse communique avec PostgreSQL à travers le réseau interne Docker.
4. PostgreSQL conserve les données nécessaires au fonctionnement du serveur.

Les ports web exposés sont liés à l'interface locale `127.0.0.1`. Cette configuration limite leur accessibilité depuis le réseau externe.

## 5. Persistance des données

Les données persistantes sont organisées comme suit :

- `synapse/data/` : configuration, clés et données générées par Synapse.
- Volume Docker `kibare_postgres_data` : données de PostgreSQL.

Ces données ne doivent pas être intégrées au dépôt Git, car elles peuvent contenir des informations sensibles ou des éléments nécessaires à la continuité du service.

## 6. Sécurité et déploiement

Le prototype adopte plusieurs mesures de base :

- Stockage du mot de passe PostgreSQL dans une variable d'environnement.
- Non-publication directe du port PostgreSQL sur l'hôte.
- Limitation des ports Element et Synapse à l'interface locale.
- Conservation des données dans des volumes persistants.

Un déploiement institutionnel nécessitera des mesures supplémentaires, notamment :

- Un nom de domaine accessible.
- HTTPS et un reverse proxy.
- Une politique de sauvegarde et de restauration.
- Une gestion rigoureuse des comptes, des rôles et des sessions.
- Des tests de sécurité et une validation de la configuration Matrix.

## 7. État de l'architecture

Cette architecture correspond à la configuration du prototype local.

Des évolutions pourront être apportées pour répondre aux besoins d'un déploiement institutionnel, notamment en matière de disponibilité, de supervision, de gestion des identités et de sécurité opérationnelle.