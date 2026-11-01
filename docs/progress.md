# État d'avancement de Kibare

Mise à jour : 1 novembre 2026. Les essais d'interface ci-dessous sont rapportés par l'équipe pendant la validation locale ; ils ne constituent pas un audit indépendant ni une homologation de sécurité.

## Synthèse

Kibare est un prototype local de messagerie Matrix. Le parcours OIDC avec TOTP et la révocation des sessions sur plusieurs appareils ont été essayés avec des comptes fictifs. L'accès direct par mot de passe Matrix est désactivé. En revanche, la preuve du chiffrement de bout en bout dans la base et le stockage média, la restauration, ainsi que le durcissement d'un déploiement restent à faire. Ne pas utiliser de données réelles ni exposer ce prototype.

## Résultats vérifiés

| Domaine | Résultat actuel | Nature de la validation |
|---|---|---|
| Authentification MFA | Un compte agent de test se connecte par SSO ; Keycloak propose ou demande un code OTP et un code valide permet de poursuivre. | Essai manuel rapporté par l'équipe dans Element en navigation privée. |
| Connexion Matrix directe | Le flux `m.login.password` n'est pas annoncé par Synapse et une tentative directe est rejetée. | Vérification locale par API. |
| Révocation | Après révocation, les sessions des appareils Element déjà connectés sont invalidées ; l'équipe constate qu'ils perdent leur session. | Essai manuel rapporté par l'équipe sur plusieurs appareils. |
| Configuration locale | Les services Compose ont démarré sains ; OIDC, le rappel SSO et l'accès de Synapse aux clés Keycloak ont répondu correctement. | Vérification locale d'intégration. |
| Tests automatiques | Les tests unitaires couvrent les politiques d'identité, de salon, de rôle et plusieurs cas des processus d'administration. | Suite locale de tests unitaires. |

## Socle et intégration réalisés

| Composant ou brique | État | Détails |
|---|---|---|
| Docker Compose | Opérationnel | Déploiement multi-conteneurs Synapse, PostgreSQL, Element, Keycloak, Portail et Admin API. |
| Synapse et PostgreSQL | Opérationnel | Configuration locale durcie avec base relationnelle persistée dans un volume Docker dédié. |
| Client web Element | Opérationnel | Thème adapté aux couleurs Kibare et serveur configuré sur `kibare.test`. |
| Secrets et isolation | Opérationnel | Fichier `.env` protégé, exclusion Git stricte des secrets et données d'exploitation. |
| Chiffrement E2EE | Configuré | Paramétré par défaut avec les protocoles Olm et Megolm sur les salons créés. |
| Minimisation des métadonnées | Opérationnel | Présence désactivée, aperçus d'URLs bloqués, rétention IP réduite à 7 jours. |

## Fonctionnalités disponibles

| Fonctionnalité | Description |
|---|---|
| Portail d'accueil | Interface d'accueil en français avec témoin dynamique de santé de l'API Matrix. |
| Configuration 2FA | Page dédiée accessible aux agents pour activer TOTP à leur convenance (`/setup-2fa.html`). |
| Console d'administration | Interface web d'administration pour enrôler des agents, gérer la 2FA et révoquer des accès (`/admin.html`). |
| Outil CLI d'exploitation | Script Python complet pour l'enrôlement, la création de salons et la révocation en ligne de commande. |
| Contrôle d'inscription | Inscription libre, comptes invités, fédération publique et mots de passe Matrix directs désactivés. |
| Authentification SSO / MFA | Authentification fédérée Keycloak avec second facteur TOTP optionnel ou obligatoire selon le compte. |
| Gestion des salons privés | Création de salons non fédérés avec historique restreint aux seuls membres présents. |
| Rôles au niveau du salon | Attribution ciblée des privilèges membre ou modérateur par salon. |

## Objectifs de durcissement et validations à venir

| Axe de travail | Action requise |
|---|---|
| Validation MFA négative | Vérifier formellement le refus explicite d'un code OTP erroné ou expiré. |
| Parcours premier login | Documenter le premier enrôlement complet : changement du mot de passe initial puis configuration TOTP. |
| Preuve de chiffrement E2EE | Inspecter PostgreSQL, les répertoires de médias et les trames réseau pour prouver l'absence de données en clair. |
| Cycle de vie après révocation | Analyser le comportement des caches locaux et le renouvellement des clés E2EE lors du départ d'un agent. |
| Tests d'habilitation stricts | Tester explicitement les tentatives d'enrôlement avec des identifiants non conformes. |
| Gouvernance des rôles | Définir la matrice des rôles institutionnels au-delà de la gestion unitaire par salon. |
| Continuité d'activité | Mettre en œuvre et éprouver une procédure complète de sauvegarde et de restauration. |
| Durcissement de production | Mettre en place un reverse proxy TLS et supprimer l'option temporaire `skip_verification`. |

## Séquence de travail recommandée

Répéter le parcours MFA avec un compte agent fictif distinct et vérifier également la réaction face à un code incorrect.

Créer un salon de démonstration via `kibare_admin.py create-room`, puis échanger un message et un fichier fictifs.

Contrôler le contenu stocké dans Synapse, PostgreSQL et le stockage média afin de consigner les observations.

Révoquer un compte en cours d'utilisation et vérifier l'invalidation immédiate des sessions ainsi que le comportement des caches résiduels.

Tester une sauvegarde complète et sa restauration dans un environnement vierge.

Ne planifier un déploiement avec des données réelles qu'après TLS, durcissement, procédures de reprise validées et revue de sécurité.

Pour les commandes reproductibles, voir [tests/README](../tests/README), [scripts/README.md](../scripts/README.md) et la [note de sécurité](security.md).
