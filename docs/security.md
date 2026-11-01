# Note de sécurité : Kibare

**Périmètre :** prototype local du Sprint technique pré-Hackathon 2026. Cette note décrit les protections présentes dans le dépôt et leurs limites ; elle ne constitue ni un audit ni une autorisation à traiter des données réelles.

## Menaces prises en compte

| Menace | Mesures présentes | Limites restantes |
|---|---|---|
| Accès d'un utilisateur non enrôlé | Inscription libre et invités désactivés ; seuls les comptes créés par un administrateur sont admis. La fédération Synapse est désactivée. | L'administrateur et l'hôte Docker restent des autorités de confiance. |
| Lecture des conversations par l'hébergeur | Les salons créés avec `kibare_admin.py create-room` activent Megolm (`m.megolm.v1.aes-sha2`) et ne sont pas fédérés. Element chiffre les événements et les pièces jointes dans un salon chiffré. | Cette intégration et l'absence de texte clair en base ou sur le réseau n'ont pas encore été démontrées. Un salon créé autrement peut ne pas être chiffré. |
| Perte d'un appareil ou départ d'un agent | `revoke` désactive le compte et ses sessions dans Synapse, désactive l'identité Keycloak et ferme ses sessions SSO. Lors d'un essai manuel rapporté, les appareils Element déjà connectés ont perdu leur session après révocation. | La révocation ne peut pas effacer les messages déjà synchronisés, déchiffrés, exportés ou capturés sur un appareil. Le renouvellement des clés E2EE après révocation doit être examiné séparément. |
| Usurpation d'identité | Connexion OIDC par Keycloak ; double facteur TOTP proposé à l'utilisateur et activable à la demande ou imposé par l'administrateur. L'authentification par mot de passe Matrix direct est désactivée ; les mots de passe temporaires sont saisis sans écho. | L'essai positif MFA a été rapporté par l'équipe en navigation privée ; vérifier encore le refus d'un code erroné/expiré et les procédures de récupération. Le secret du compte bootstrap Keycloak est conservé dans `.env` et doit être protégé. |
| Exposition réseau | PostgreSQL n'est pas publié ; accueil, Element et Synapse sont liés à `127.0.0.1`. Les salons créés par l'outil refusent la fédération. | Keycloak et Synapse utilisent HTTP local ; `skip_verification` contourne les contrôles de conformité des métadonnées OIDC pour ce prototype. Pas de TLS, reverse proxy de production, durcissement hôte ni validation multi-machine. Ne pas exposer les ports. |
| Perte ou altération des données | PostgreSQL utilise un volume Docker persistant ; secrets et données Synapse sont ignorés par Git. | Aucune sauvegarde/restauration automatisée ou testée ; volume et serveur restent des points uniques de défaillance. |

## Données et métadonnées visibles par le serveur

Dans un salon Matrix effectivement chiffré de bout en bout, Synapse stocke les événements chiffrés et ne possède pas les clés de déchiffrement des appareils. Element chiffre également le contenu des fichiers avant leur dépôt dans le stockage de médias. Cette propriété doit être vérifiée par inspection de la base, du stockage de fichiers et du trafic réseau avant toute présentation comme garantie acquise. Les salons non chiffrés exposent leur contenu au serveur.

Même pour un salon chiffré, l'hébergeur peut observer les identifiants des comptes, les adhésions/invitations et les changements de salons, les horaires et tailles approximatives des événements, les connexions/sessions, les adresses IP vues par le serveur, ainsi que l'activité de synchronisation. Il détient la base, les journaux, les clés de signature Synapse et les métadonnées nécessaires au routage. Les sauvegardes peuvent également contenir ces données. Les salons créés par l'outil limitent l'historique à la période depuis l'adhésion et ne fédèrent pas.

## Contrôles opérationnels

Garder impérativement `.env`, `synapse/data/`, le jeton administrateur, les clés et les sauvegardes hors du dépôt et hors des journaux partagés.

N'utiliser que des comptes et des informations fictifs pendant tous les tests locaux.

Pour tester un nouveau parcours MFA, utiliser une fenêtre privée fraîche. La session SSO Keycloak déjà ouverte dans un navigateur peut éviter une nouvelle demande d'identifiants. Le code TOTP valide l'authentification et n'est pas l'approbation cryptographique d'un nouvel appareil Matrix.

Créer les salons de démonstration avec `kibare_admin.py create-room`, puis vérifier l'indicateur de chiffrement Element avant d'envoyer un message fictif.

Ne pas confondre l'état de disponibilité du portail avec une validation du chiffrement, de l'identité ou de la sécurité.

Ne pas publier les ports sur un réseau externe ni utiliser le prototype pour des communications de service réelles.

## Limites bloquantes avant production

Plusieurs points doivent être validés avant tout usage en production :

Compléter le test MFA positif rapporté par l'équipe avec un code OTP invalide ou expiré, ainsi que les scénarios de récupération de compte.

Remplacer le mode développement Keycloak et le HTTP local par un déploiement durci et TLS, puis retirer `skip_verification` avant toute exposition hors de la machine.

Démontrer le chiffrement effectif des messages et fichiers par inspection de Synapse/PostgreSQL, du stockage de médias et des flux réseau.

Documenter précisément les limites observées après révocation : les sessions sont invalidées sur les appareils testés, mais les contenus déjà reçus et déchiffrés localement ne sont pas effaçables à distance.

Définir les rôles institutionnels, le processus d'habilitation et la séparation des responsabilités au-delà des rôles par salon.

Ajouter une politique de sauvegarde/restauration testée, la supervision opérationnelle, la gestion des mises à jour, la rétention et un audit indépendant.

Le TOTP s'appuie sur le mécanisme de Keycloak ; aucune cryptographie MFA n'est développée par Kibare. Le flux MFA positif et la perte des sessions Element après révocation ont été essayés manuellement par l'équipe ; ces essais ne démontrent ni le chiffrement E2EE effectif, ni l'effacement des caches locaux, ni la sécurité d'un déploiement de production. **Kibare reste un prototype ; n'utilisez aucune donnée réelle.**
