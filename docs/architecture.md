# Architecture technique de Kibare

## Présentation

Kibare est un prototype local de messagerie fondé sur Matrix. L'organisation héberge elle-même les composants et conserve ses données sur sa machine ou son infrastructure. Aucun service tiers n'est indispensable à l'exécution.

## Composants

| Service | Rôle | Adresse dans le prototype |
|---|---|---|
| Portail Kibare / Nginx | Accueil français responsive, liens vers la messagerie et témoin d'API Matrix | `http://127.0.0.1:8081` |
| Element Web | Client de messagerie aux couleurs Kibare, connecté au homeserver local | `http://127.0.0.1:8080` |
| Matrix Synapse | Comptes, sessions, salons et événements Matrix | `http://127.0.0.1:8008` |
| Keycloak | Fournisseur OpenID Connect local et gestion du second facteur TOTP | `http://127.0.0.1:8082` |
| PostgreSQL | Persistance Synapse sur un volume Docker nommé | Réseau Docker uniquement |

`scripts/kibare_admin.py` est un outil d'exploitation local, pas un service web. Il s'appuie sur les API officielles Matrix/Synapse pour enrôler des agents, créer des salons, attribuer un rôle par salon et révoquer un compte.

## Flux

1. Le navigateur charge le portail statique ; son indicateur interroge uniquement `/_matrix/client/versions` via le proxy local Nginx.
2. L'agent ouvre Element, qui échange avec l'API Matrix de Synapse.
3. Synapse écrit dans PostgreSQL sur le réseau interne Compose.
4. Les salons créés avec l'outil d'administration sont privés, chiffrés avec Megolm, non fédérés, limités aux invités et configurés pour ne montrer l'historique qu'aux utilisateurs déjà présents.

La configuration Element fixe le serveur `kibare.test`, désactive les inscriptions, les invités et les connexions tierces, et utilise le thème clair. Synapse délègue la connexion à Keycloak en OIDC et désactive l'authentification par mot de passe Matrix. Les endpoints OIDC publics du navigateur utilisent localhost ; les échanges de jetons et de clés entre conteneurs utilisent le réseau interne Compose.

Keycloak impose TOTP lors de la première connexion et à chaque compte enrôlé. Les services web sont liés à `127.0.0.1` et Keycloak utilise `start-dev` pour le prototype. Synapse ignore la validation stricte des métadonnées OIDC (`skip_verification`) car les endpoints du prototype sont en HTTP ; ce contournement doit être retiré avec la mise en place de TLS avant toute exposition hors machine.

Le TOTP constitue le second facteur de connexion auprès de Keycloak. La vérification cryptographique des appareils Matrix est un autre mécanisme : un appareil Element nouvellement ajouté peut nécessiter l'approbation d'un appareil déjà vérifié ou une clé de récupération pour accéder aux clés E2EE. Cette approbation ne remplace pas l'authentification SSO/MFA.

## Inscription et administration

`start.sh` génère localement les secrets PostgreSQL, OIDC et Keycloak, rend le fichier d'import du realm hors Git, initialise ou ajuste `synapse/data/homeserver.yaml`, désactive l'inscription libre, les invités, la fédération et les mots de passe Matrix, puis démarre la pile. L'inscription partagée est réservée au bootstrap local du premier administrateur par la commande Synapse documentée dans le README.

Les agents sont créés par un administrateur dans Keycloak et Synapse avec un mot de passe temporaire saisi de façon masquée ; leur premier accès leur impose un changement de mot de passe et l'enrôlement TOTP. Ils ne reçoivent pas de privilège serveur. Lors d'un essai manuel rapporté par l'équipe, un compte agent a terminé le parcours SSO avec un code OTP dans une fenêtre privée. La révocation désactive le compte et les sessions dans Synapse et Keycloak ; l'équipe a observé que les appareils Element déjà connectés perdaient leur session. Cette action ne peut effacer les anciens messages déjà déchiffrés et mis en cache sur un appareil. Les rôles `member` et `moderator` s'appliquent dans un seul salon et ne remplacent pas une politique institutionnelle complète.

## Données persistantes et limites

- `synapse/data/` contient la configuration, les clés de signature et le stockage Synapse ; ce dossier est ignoré par Git.
- `kibare_postgres_data` conserve la base ; ne pas supprimer ce volume sans sauvegarde.
- `.env` contient des secrets et reste local ; le jeton administrateur est gardé dans le terminal d'administration.
- Le portail n'interprète aucun message et n'est pas un client de chat.
- Les essais MFA et révocation positifs sont rapportés par l'équipe ; le refus de codes TOTP invalides, la démonstration E2EE, les sauvegardes testées et TLS restent à traiter avant tout usage de données réelles.

Voir [la note de sécurité](security.md), [les licences](open-source.md) et [la revue des exigences du sprint](requirements-review.md).
