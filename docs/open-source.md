# Technologies open source

Kibare adopte l'engagement **Étendre et adapter** : il assemble et configure des logiciels libres existants et ajoute un portail et des opérations d'administration adaptés à un prototype institutionnel. Aucune cryptographie ni aucun protocole ne sont développés par l'équipe.

| Composant | Usage | Licence du projet | Projet |
|---|---|---|---|
| Kibare | Portail, orchestration, script d'administration et documentation | MIT | [Dépôt Kibare](https://github.com/only-for-geek/Kibare) |
| Matrix | Protocole ouvert de messagerie | Apache-2.0 | [Spécification Matrix](https://github.com/matrix-org/matrix-spec) |
| Synapse `v1.163.0` | Serveur Matrix et API d'administration | AGPL-3.0 | [Element Synapse](https://github.com/element-hq/synapse) |
| Element Web | Client de messagerie web, image épinglée par digest dans Compose | AGPL-3.0 | [Element Web](https://github.com/element-hq/element-web) |
| Keycloak `26.4.2` | Fournisseur OpenID Connect et TOTP | Apache-2.0 | [Keycloak](https://github.com/keycloak/keycloak) |
| PostgreSQL | Persistance | PostgreSQL License | [PostgreSQL](https://www.postgresql.org/about/licence/) |
| Nginx `1.29.3-alpine` | Portail statique et contrôle local de disponibilité | BSD-2-Clause | [Nginx](https://nginx.org/) |
| Docker Engine / Compose | Conteneurisation et orchestration | Apache-2.0 | [Docker Engine](https://github.com/moby/moby), [Compose](https://github.com/docker/compose) |
| Python 3 | Script d'administration et tests standard-library | PSF License | [Python](https://docs.python.org/3/license.html) |
| OpenSSL | Génération locale de secrets au démarrage | Apache-2.0 | [OpenSSL](https://github.com/openssl/openssl) |

Les composants tiers restent régis par leurs licences, leurs avis de copyright et les conditions de distribution de leurs images. Cette liste indique les licences des projets amont ; elle ne remplace pas l'inventaire des notices des versions effectivement distribuées. Aucune API hébergée ou plateforme tierce n'est requise pour le fonctionnement local.

Le fichier [LICENSE](../LICENSE) couvre le code Kibare, et non les logiciels tiers.
