# Gestion des comptes Kibare

Ce guide explique l'utilisation de `kibare_admin.py` pour créer et révoquer des comptes d'agents. Les commandes sont à lancer depuis la racine du dépôt, avec les services démarrés par `./start.sh`. Utilisez uniquement des comptes fictifs pour vos essais.

## 1. Créer le premier administrateur

À faire une seule fois après l'installation. Sur la machine qui héberge Kibare, lancez :

```bash
docker compose exec synapse register_new_matrix_user \
  -c /data/homeserver.yaml --admin http://localhost:8008
```

Le programme demande un nom d'utilisateur et un mot de passe. Ce compte administre le serveur ; les comptes d'agents créés ensuite par Kibare ne sont pas administrateurs.

## 2. Ouvrir une session d'administration

Depuis le terminal qui servira aux opérations :

```bash
export KIBARE_ADMIN_TOKEN="$(python3 scripts/kibare_admin.py login NOM_ADMIN)"
```

Remplacez `NOM_ADMIN` par le nom local du compte administrateur, sans `@` ni `:kibare.test`. La commande ouvre le navigateur ; connectez-vous avec Keycloak et votre code TOTP. Le jeton Matrix est conservé dans la variable d'environnement du terminal et n'est pas affiché par la commande.

Gardez ce jeton privé. Après les opérations, supprimez-le de l'environnement :

```bash
unset KIBARE_ADMIN_TOKEN
```

Si le jeton expire, relancez `login`.

Si une commande répond `Invalid access token passed`, la session Matrix est absente, invalide ou expirée. Dans le même terminal, reconnectez-vous puis relancez la commande d'administration :

```bash
export KIBARE_ADMIN_TOKEN="$(python3 scripts/kibare_admin.py login NOM_ADMIN)"
```

La commande `login` écrit le jeton seul sur la sortie standard pour que cette affectation fonctionne ; les messages du navigateur sont envoyés sur la sortie d'erreur.

## 3. Enrôler un agent

```bash
python3 scripts/kibare_admin.py enroll test --display-name "Compte de test"
```

Le script demande deux fois un mot de passe temporaire d'au moins 14 caracteres, sans l'afficher. Il cree l'identite Keycloak et le compte Matrix non-administrateur `@test:kibare.test`. A la premiere connexion SSO dans Element, l'agent devra changer son mot de passe. La configuration de la double authentification TOTP est proposee mais non obligatoire : l'agent peut le faire depuis `http://127.0.0.1:8081/setup-2fa.html` ou plus tard depuis son compte Keycloak. L'administrateur peut l'imposer a tout moment depuis le panneau d'administration.

Le jeton d'administration est vérifié avant que le script demande ce mot de passe temporaire.

Pour un deuxième compte fictif :

```bash
python3 scripts/kibare_admin.py enroll user --display-name "Utilisateur de test"
```

Si le compte Matrix existe déjà, l'enrôlement ajoute son identité Keycloak avec le même nom ; le compte existant est ainsi associé lors de sa première connexion OIDC. Un identifiant déjà utilisé par Keycloak est refusé et aucun mot de passe existant n'est réinitialisé.
Un compte Matrix déjà désactivé n'est pas réactivé par `enroll` : utilisez un nouvel identifiant de test ou faites confirmer sa réactivation par l'administrateur avant de la réaliser séparément.

## 4. Révoquer un agent

```bash
python3 scripts/kibare_admin.py revoke @user:kibare.test
```

La désactivation invalide les sessions du compte dans Synapse, désactive l'identité Keycloak et ferme ses sessions SSO. Pour vérifier le résultat, tentez de vous connecter de nouveau avec ce compte ou vérifiez qu'il ne peut plus synchroniser de nouveaux messages. Un appareil peut toutefois conserver des messages qu'il a déjà reçus et déchiffrés ; la révocation ne peut pas effacer ces copies locales.

Dans Element, le menu Paramètres, puis Appareils, puis Supprimer cet appareil ne déconnecte que l'appareil courant. La commande `revoke` est une action d'administration sur le compte entier : elle vise à invalider les sessions de tous ses appareils. Ne pas confondre ces deux actions avec la désactivation manuelle dans les paramètres de compte Element, qui est une opération distincte et potentiellement permanente.

## 5. Parcours complet d'exemple

```bash
export KIBARE_ADMIN_TOKEN="$(python3 scripts/kibare_admin.py login admin)"
python3 scripts/kibare_admin.py enroll test --display-name "Compte de test"
python3 scripts/kibare_admin.py enroll user --display-name "Utilisateur de test"
python3 scripts/kibare_admin.py revoke @user:kibare.test
unset KIBARE_ADMIN_TOKEN
```

Si les comptes existent déjà, omettez les commandes `enroll` correspondantes et exécutez seulement la révocation.

## Commandes disponibles

```bash
python3 scripts/kibare_admin.py --help
python3 scripts/kibare_admin.py login --help
python3 scripts/kibare_admin.py enroll --help
python3 scripts/kibare_admin.py revoke --help
```

L'outil gère également les salons privés chiffrés et les rôles :

La commande `create-room` crée un salon privé, non fédéré et configuré pour le chiffrement Megolm. Ajoutez `--invite @agent:kibare.test` pour chaque agent à inviter.

La commande `set-room-role SALON UTILISATEUR member|moderator` attribue un rôle au sein d'un salon donné.

Pour ces commandes, voir les exemples du fichier [README.md](../README.md). L'outil en ligne de commande ne fournit actuellement ni commande de liste des comptes, ni réactivation d'un compte révoqué (la console web `/admin.html` permet quant à elle de visualiser et forcer la 2FA). Ce prototype ne doit pas servir à des échanges réels ou sensibles.
