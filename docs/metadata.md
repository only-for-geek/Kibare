# Metadonnees dans Kibare

Dans le cadre des exigences institutionnelles, l'equipe documente ce que le serveur voit malgre le chiffrement, et les mesures prises pour reduire ces informations.

## Ce que le serveur ne peut pas lire

Grace au chiffrement de bout en bout base sur les protocoles Olm et Megolm :

Le contenu des messages textuels est chiffre cote client. Seuls les appareils des destinataires legitimes possedent les cles pour dechiffrer.

Les fichiers et pieces jointes sont egalement chiffres avant leur telechargement. Le serveur ne stocke que des blocs de donnees opaques.

Meme en accedant directement a la base de donnees PostgreSQL, un administrateur systeme ne peut lire aucun echange en clair dans un salon chiffre.

## Ce que le serveur voit malgre tout

Pour acheminer les messages et synchroniser les appareils, le serveur conserve certaines informations de routage.

| Information visible | Description | Risque |
|---|---|---|
| Graphe social | Les identifiants des utilisateurs et la liste des membres de chaque salon. | Permet de deduire qui collabore avec qui. |
| Horodatages | L'heure d'emission de chaque evenement et la frequence des messages. | Permet d'analyser les periodes d'activite. |
| Taille des flux | La taille en octets des blocs chiffres et des fichiers dans le stockage media. | Peut donner des indices sur le type de contenu. |
| Adresses IP | Les adresses depuis lesquelles les appareils se connectent, les versions de clients et les identifiants d'appareils. | Permet de localiser approximativement les agents. |

## Mesures de reduction des metadonnees dans Kibare

Presence desactivee (`presence.enabled: false`) : Synapse ne diffuse plus si un agent est en ligne ou inactif. Aucun statut ni horodatage d'activite n'est enregistre entre agents.

Aperçus de liens desactives (`url_preview_enabled: false`) : le serveur ne charge plus les pages partagees pour generer des aperçus, evitant l'exposition de l'adresse IP du serveur aux sites tiers.

Retention des adresses IP limitee (`user_ips_max_age: 7d`) : la table associant chaque utilisateur et appareil a une adresse IP est purgee automatiquement apres 7 jours.

Purge rapide des suppressions (`redaction_retention_period: 1d`) : les metadonnees des messages supprimes sont retirees apres 1 jour au lieu de plusieurs semaines.

Telemetrie desactivee (`report_stats: false`, `stats.enabled: false`) : aucune metrique sur les volumes ou les salons n'est remontee.

Chiffrement actif par defaut : tout salon cree dans Kibare a le chiffrement Megolm active par defaut, le serveur ne voit donc jamais le texte en clair par inadvertance.

## Recommandations pour un deploiement operationnel

Pour reduire encore les metadonnees au niveau reseau :

Faire transiter les connexions par un VPN d'Etat ou un reseau prive interne, de sorte que le serveur Kibare ne voie que des adresses IP privees.

Acheminer le trafic via un reverse proxy TLS pour uniformiser les flux reseau et masquer les en-tetes serveur.
