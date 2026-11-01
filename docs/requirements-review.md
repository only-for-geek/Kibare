# Revue du brief — Sprint technique pré-Hackathon 2026

Cette revue distingue les fonctionnalités configurées des contrôles effectivement essayés. Les tests d'interface MFA et de révocation sont rapportés par l'équipe pendant les essais locaux ; ils ne constituent pas une certification ni un audit indépendant.

## Exigences principales

| Exigence | État au 1 novembre 2026 | Éléments probants et travaux restants |
|---|---|---|
| Logiciels open source et licence OSI | **Présent** | Licence MIT à la racine ; inventaire des licences amont dans [open-source.md](open-source.md). |
| Installation souveraine sans service tiers indispensable | **Prototype local présent** | Compose auto-hébergé et services liés à `127.0.0.1`. Il reste à définir et tester l'exploitation de production. |
| Authentification forte avec second facteur | **Parcours positif testé** | Essai manuel rapporté : connexion SSO d'un agent en navigation privée, demande TOTP, saisie d'un code valide puis accès. Synapse n'annonce pas `m.login.password`. À compléter : essai avec code invalide/expiré et tests de récupération. |
| Agents préalablement enrôlés | **Contrôle de base présent** | Inscription libre et invités désactivés ; un administrateur crée les identités. Documenter l'essai de refus pour un identifiant non enrôlé. |
| Révocation des sessions sur les appareils | **Essai manuel positif** | L'équipe rapporte qu'après révocation, les appareils Element déjà connectés perdent leur session. Cela ne supprime pas les messages déjà synchronisés ou déchiffrés sur un appareil. |
| Gestion des rôles | **Partielle** | Rôles `member` et `moderator` attribuables par salon ; rôles institutionnels et séparation des responsabilités non définis. |
| Confidentialité des messages vis-à-vis du serveur | **Configurée mais non démontrée** | Megolm est activé pour les salons créés par l'outil ; inspecter PostgreSQL, médias et trafic pour prouver qu'aucun contenu lisible n'y est conservé. |
| Minimisation et documentation des métadonnées | **Documentée** | Voir [security.md](security.md) : l'hébergeur voit toujours identités, adhésions, horaires, tailles approximatives, IP et sessions. |
| Note de sécurité | **Présente** | [Note de sécurité](security.md) : menaces, protections, métadonnées et limites. |

## Livrables, innovation et démonstration

| Élément | État |
|---|---|
| README français avec concept, architecture, installation et limites | Présent ; renvoie aux documents détaillés. |
| Dépôt public et historique de commits progressifs | Le dépôt existe ; l'historique du sprint et la publication restent à gérer par l'équipe. Aucun push n'a été effectué par ce travail. |
| Comptes fictifs | À créer/gérer localement pour la démonstration ; ne jamais versionner de secrets ou comptes actifs. |
| Vidéo de démonstration (3 min) | À enregistrer après les scénarios fonctionnels complémentaires. |
| Innovation adaptée | Portail en français, salons d'équipe privés/chiffrés/non fédérés et révocation ; compléter les preuves de chiffrement et la démonstration. |
| Interface/langue nationale | Interface en français ; une langue nationale n'est pas encore intégrée. |
| Contribution au projet open source amont | Aucune contribution externe n'a été soumise. |
| Tests automatisés | Tests unitaires locaux des politiques et workflows ; ils ne remplacent pas les essais E2EE, MFA complet et restauration. |

## Distinction importante : MFA et appareils Matrix

Le code TOTP valide l'authentification SSO auprès de Keycloak. La vérification d'un appareil Matrix et le partage des clés E2EE sont des mécanismes distincts : un nouvel appareil peut demander l'approbation d'un appareil déjà vérifié ou l'utilisation d'une clé de récupération. Cette étape de confiance cryptographique ne remplace ni le mot de passe ni le TOTP.

## Conclusion

Kibare possède désormais un parcours MFA positif et une révocation des sessions déjà essayés manuellement, en plus de la connexion Matrix directe par mot de passe désactivée. Ces résultats ne prouvent pas à eux seuls la confidentialité E2EE, la résilience ou l'aptitude à traiter des données réelles. **Le système demeure un prototype local ; ne pas exposer les services ni y utiliser de données réelles.**

Voir le plan de validation opérationnel dans [progress.md](progress.md) et les étapes reproductibles dans [tests/README](../tests/README).
