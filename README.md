# Kibare — messagerie institutionnelle souveraine

Kibare est un prototype de messagerie pour les agents publics, construit sur le protocole ouvert Matrix. Il associe Synapse, Element Web et PostgreSQL dans une installation locale contrôlée par l'organisation. L'interface d'accueil en français met en avant l'état du serveur et les accès utiles ; Element reste le client de conversation.

> **Prototype de sélection — pas prêt pour des échanges réels.** L'équipe a rapporté un essai positif de connexion agent avec TOTP et la perte des sessions Element testées après révocation. Le chiffrement E2EE n'a pas encore été démontré dans le stockage ; Synapse contourne aussi la validation stricte des métadonnées OIDC pour permettre HTTP local. Utilisez exclusivement des comptes, fichiers et messages fictifs, et ne publiez pas les services.

## Ce qui est déjà en place

- **Déploiement autonome :** Docker Compose, PostgreSQL persistant et services publiés uniquement sur `127.0.0.1`.
- **Inscription maîtrisée :** l'inscription libre, les invités et la fédération sont désactivés lors du lancement ; les agents sont créés par un administrateur.
- **Authentification à deux facteurs :** Keycloak fournit l'authentification OIDC et impose la configuration TOTP avant l'accès. Les mots de passe Matrix ne permettent plus de connexion directe.
- **Salons institutionnels :** l'outil d'administration crée des salons privés, non fédérés, chiffrés avec Megolm et limités à l'historique depuis l'adhésion.
- **Contrôle d'accès :** enrôlement, révocation des sessions et rôles membre/modérateur par salon.
- **Interface Kibare :** accueil responsive en français et client Element configuré avec l'identité visuelle Kibare.

Le TOTP est le facteur d'authentification Keycloak. L'approbation cryptographique d'un nouvel appareil Matrix, lorsqu'elle est nécessaire pour les clés E2EE, est un mécanisme distinct. Voir l'[état de validation](docs/progress.md), la [revue du brief](docs/requirements-review.md) et les [scénarios de test](tests/README).

Le périmètre et les limites sont décrits dans [la revue des exigences](docs/requirements-review.md), [la note de sécurité](docs/security.md) et [l'état d'avancement](docs/progress.md).

## Démarrage local

Prérequis : Git, Docker Engine avec le plugin `docker compose`, OpenSSL et Python 3.

```bash
git clone https://github.com/only-for-geek/Kibare.git
cd Kibare
chmod +x start.sh
./start.sh
```

Le script génère les secrets locaux, initialise Synapse si nécessaire, vérifie la configuration, puis démarre les services. Les données existantes sont conservées.

| Service | Adresse locale |
|---|---|
| Accueil Kibare | http://127.0.0.1:8081 |
| Messagerie Element | http://127.0.0.1:8080 |
| API Matrix | http://127.0.0.1:8008 |
| Identité et MFA Keycloak | http://127.0.0.1:8082 |

### Créer le premier administrateur

Sur la machine qui héberge Kibare, créer le compte administrateur après le démarrage :

```bash
docker compose exec synapse register_new_matrix_user \
  -c /data/homeserver.yaml --admin http://localhost:8008
```

La commande demande le nom et le mot de passe sans les inscrire dans l'historique du terminal. Ce compte est réservé à l'administration ; les comptes d'agents créés par l'outil ne sont jamais administrateurs.

Le compte `admin` est également précréé dans le realm Keycloak `kibare`. Pour sa première connexion OIDC, récupérez son mot de passe temporaire localement depuis `.env` :

```bash
awk -F= '$1 == "KIBARE_INITIAL_ADMIN_PASSWORD" { print $2 }' .env
```

Connectez-vous ensuite dans Element avec le bouton SSO **Kibare** et l'identifiant `admin`. Keycloak exige la configuration d'une application d'authentification TOTP. Après ce premier enrôlement MFA, cette même identité OIDC est associée au compte Matrix administrateur.

### Enrôler un agent et gérer un salon

La commande `login` ouvre le navigateur pour authentifier l'administrateur via Keycloak et TOTP. Le jeton Matrix obtenu est gardé dans le terminal courant ; fermez la session ou exécutez `unset KIBARE_ADMIN_TOKEN` après usage.

```bash
export KIBARE_ADMIN_TOKEN="$(python3 scripts/kibare_admin.py login admin)"
python3 scripts/kibare_admin.py enroll agent.dsi --display-name "Agent DSI"
python3 scripts/kibare_admin.py create-room --name "Équipe DSI" \
  --invite @agent.dsi:kibare.test
# Copier l'identifiant !...:kibare.test renvoyé par create-room.
python3 scripts/kibare_admin.py set-room-role \
  '!copier-identifiant:kibare.test' @agent.dsi:kibare.test moderator
python3 scripts/kibare_admin.py revoke @agent.dsi:kibare.test
unset KIBARE_ADMIN_TOKEN
```

Les commandes `enroll`, `create-room`, `set-room-role` et `revoke` doivent être lancées par un administrateur. `enroll` crée l'identité Keycloak et associe (ou précrée) le compte Matrix ; le mot de passe temporaire est saisi sans écho, puis changé par l'agent à sa première connexion. L'agent configure alors son authentificateur TOTP. Les identifiants déjà existants dans Matrix peuvent être migrés en enrôlant le même nom. Seuls les rôles `member` et `moderator` sont attribuables dans un salon. Les instructions détaillées figurent dans [scripts/README.md](scripts/README.md) et les options sont dans `python3 scripts/kibare_admin.py --help`.

## Vérifications

```bash
docker compose config -q
python3 -m unittest discover -s tests -v
bash -n start.sh
```

Les tests unitaires couvrent les identifiants locaux, les politiques des salons/rôles et la configuration TOTP d'enrôlement. En complément, l'équipe a rapporté un essai positif de connexion agent avec OTP et de révocation des sessions des appareils testés. Les tests automatisés ne démontrent pas le chiffrement E2EE ni la restauration ; les essais manuels restant à faire sont listés dans [tests/README](tests/README).

## Technologies et licence

Le code Kibare est publié sous **MIT**. Les composants tiers conservent leurs licences respectives ; leurs versions et liens sont recensés dans [docs/open-source.md](docs/open-source.md).

**Engagement : Étendre et adapter.** Kibare adapte l'écosystème Matrix/Element existant pour un usage institutionnel plutôt que de développer une cryptographie ou un protocole propriétaire.
