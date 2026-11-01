# Minimisation des métadonnées dans Kibare

## 1. Contexte et principe

Dans le cadre des exigences institutionnelles et des critères d'évaluation du projet Kibare :
> *« Le serveur ne peut pas lire les messages ; l'équipe documente ce qu'il voit malgré tout (qui échange avec qui, à quel moment) et les mesures prises pour le réduire. »*

Ce document détaille l'état des métadonnées transitant sur le serveur Kibare (Matrix Synapse) et les configurations techniques concrètes déployées pour les restreindre au strict minimum opérationnel.

---

## 2. Ce que le serveur ne peut PAS lire

Grâce au chiffrement de bout en bout (E2EE) basé sur les protocoles ouverts et éprouvés **Olm** (dérivé du Double Ratchet de Signal) et **Megolm** :

* **Contenu des messages textuels :** Seuls les appareils des destinataires légitimes possèdent les clés cryptographiques pour déchiffrer le corps du texte.
* **Fichiers et pièces jointes :** Les fichiers transmis sont chiffrés côté client avant téléversement. Le serveur ne stocke que des blocs de données binaires chiffrés opaques.
* **Historique des conversations :** Même en accédant directement à la base de données PostgreSQL ou aux volumes disques de Synapse, un administrateur système ou un attaquant ne peut lire aucun échange en clair.

---

## 3. Ce que le serveur voit malgré tout (Limites inhérentes au routage)

Pour acheminer les messages vers les bons destinataires et synchroniser les appareils, le serveur central conserve nécessairement certaines informations de routage et d'état :

| Métadonnée visible | Description | Risque associé |
|--------------------|-------------|----------------|
| **Le graphe social (*Qui échange avec qui*)** | Les identifiants des utilisateurs (`@agent:kibare.test`) et la liste des membres appartenant à chaque salon (`!salon_id:kibare.test`). | Permet de déduire qui collabore avec qui et la structure organisationnelle. |
| **L'horodatage des événements (*À quel moment*)** | L'heure exacte d'émission de chaque événement (`origin_server_ts`) et le volume/fréquence des messages. | Permet d'analyser les périodes d'activité ou de déceler des pics de communication de crise. |
| **Taille approximative des flux** | La taille en octets des blocs chiffrés et des fichiers stockés dans le magasin de médias (`media_store`). | Peut donner des indices sur le type de contenu (ex: document lourd vs texte court). |
| **Adresses IP et empreintes techniques** | Les adresses IP réseau depuis lesquelles les appareils se connectent, les versions de clients et les identifiants d'appareils (*Device IDs*). | Permet de géolocaliser approximativement les agents ou d'identifier leur matériel de connexion. |

---

## 4. Mesures concrètes prises par Kibare pour réduire les métadonnées

Afin de contrer ces risques, Kibare applique une politique stricte de durcissement et de minimisation, tant au niveau du serveur (`homeserver.yaml` / `start.sh`) que du client web (`element/config.json`) :

### 4.1. Désactivation totale de la présence (`presence.enabled: false`)
* **Problème par défaut :** Synapse diffuse en continu si un agent est en ligne, inactif ou déconnecté, ainsi que l'heure de sa dernière activité.
* **Mesure Kibare :** Le service de présence est **entièrement désactivé**. Aucun statut en ligne ni horodatage d'activité n'est enregistré ni diffusé entre agents, empêchant toute surveillance des habitudes de travail.

### 4.2. Suppression des aperçus de liens (`url_preview_enabled: false`)
* **Problème par défaut :** Lorsqu'un utilisateur partage une URL, le serveur Matrix tente de charger la page pour générer un aperçu, exposant l'adresse IP du serveur et les centres d'intérêt des utilisateurs aux sites tiers.
* **Mesure Kibare :** Les prévisualisations d'URLs sont désactivées côté serveur et côté interface client (`UIFeature.urlPreviews: false`).

### 4.3. Rétention stricte des adresses IP (`user_ips_max_age: 7d`)
* **Problème par défaut :** Synapse conserve indéfiniment la table d'association entre chaque utilisateur, appareil et adresse IP publique.
* **Mesure Kibare :** La durée maximale de conservation des adresses IP dans la base de données est limitée à **7 jours** (puis purgée automatiquement par Synapse).

### 4.4. Purge rapide des événements caviardés (`redaction_retention_period: 1d`)
* **Problème par défaut :** Lorsqu'un message est supprimé (*redacted*), les métadonnées de l'événement supprimé restent indexées pendant plusieurs semaines.
* **Mesure Kibare :** Le délai de rétention des événements supprimés est abaissé à **1 jour**.

### 4.5. Désactivation de la télémétrie et des statistiques d'usage
* **Mesure Kibare :** `report_stats: false` et `stats.enabled: false` empêchent toute agrégation interne ou remontée de métriques sur les volumes et salons.

### 4.6. Chiffrement de bout en bout activé par défaut
* **Mesure Kibare :** Tout salon créé dans Kibare a le chiffrement activé par défaut (`io.element.e2ee.default: true`), garantissant que le serveur ne voit jamais le texte en clair par inadvertance.

---

## 5. Recommandations pour le déploiement opérationnel

Pour minimiser encore davantage les métadonnées au niveau réseau lors de la mise en production institutionnelle :

1. **Réseau privé / VPN institutionnel :** Faire transiter les connexions des agents au travers d'un VPN d'État ou d'un réseau fermé pour que le serveur Kibare ne voie que des adresses IP privées internes.
2. **Reverse Proxy durci :** Masquer les en-têtes serveurs et acheminer le trafic via un reverse proxy TLS (ex: Caddy) pour uniformiser les flux réseau.
