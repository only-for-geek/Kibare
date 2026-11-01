# État d'avancement de Kibare

**Mise à jour : 1 novembre 2026.** Les essais d'interface ci-dessous sont rapportés par l'équipe pendant la validation locale ; ils ne constituent pas un audit indépendant ni une homologation de sécurité.

## Synthèse

Kibare est un prototype local de messagerie Matrix. Le parcours OIDC avec TOTP et la révocation des sessions sur plusieurs appareils ont maintenant été essayés avec des comptes fictifs. L'accès direct par mot de passe Matrix est désactivé. En revanche, la preuve du chiffrement de bout en bout dans la base et le stockage média, la restauration, ainsi que le durcissement d'un déploiement restent à faire. **Ne pas utiliser de données réelles ni exposer ce prototype.**

## Résultats vérifiés

| Domaine | Résultat actuel | Nature de la validation |
|---|---|---|
| Authentification MFA | Un compte agent de test se connecte par SSO ; Keycloak demande un code OTP et un code valide permet de poursuivre. | Essai manuel rapporté par l'équipe dans Element en navigation privée. |
| Connexion Matrix directe | Le flux `m.login.password` n'est pas annoncé par Synapse et une tentative directe est rejetée. | Vérification locale par API. |
| Révocation | Après révocation, les sessions des appareils Element déjà connectés sont invalidées ; l'équipe constate qu'ils perdent leur session. | Essai manuel rapporté par l'équipe sur plusieurs appareils. |
| Configuration locale | Les services Compose ont démarré healthy ; OIDC, le callback SSO et l'accès de Synapse aux clés Keycloak ont répondu correctement. | Vérification locale d'intégration. |
| Tests automatiques | Les tests unitaires couvrent les politiques d'identité/salon/rôle et plusieurs cas des workflows admin, dont les jetons invalides et les comptes désactivés. | Suite locale ; elle ne remplace pas les essais d'interface. |

La connexion d'un nouvel appareil et la vérification des clés E2EE sont distinctes du MFA : le TOTP prouve l'authentification auprès de Keycloak ; la vérification d'appareil Matrix protège l'identité cryptographique et le partage des clés de chiffrement. Un nouvel appareil peut nécessiter une vérification par un appareil déjà approuvé ou une clé de récupération, selon l'état de la sauvegarde des clés et du compte.

## Fonctionnalités présentes

- [x] Portail Kibare responsive en français avec témoin de disponibilité de l'API Matrix.
- [x] Déploiement local Docker Compose : Synapse, PostgreSQL, Element Web, Keycloak et portail.
- [x] Inscription libre, invités, fédération et authentification Matrix par mot de passe désactivés.
- [x] SSO OpenID Connect Keycloak avec TOTP exigé aux identités enrôlées.
- [x] Enrôlement administrateur et révocation du compte dans Synapse et Keycloak.
- [x] Salons privés créés par l'outil configurés pour Megolm, non-fédération et historique réservé aux membres présents.
- [x] Rôles `member` et `moderator` au niveau d'un salon.
- [x] Documentation de sécurité, d'architecture, d'exploitation et de licences ; licence MIT.

## À démontrer ou à terminer

- [ ] Vérifier explicitement qu'un code OTP erroné ou expiré est refusé.
- [ ] Consigner le test de première connexion d'un agent (changement du mot de passe temporaire puis configuration TOTP), si ce cas n'a pas déjà été observé pour le compte testé.
- [ ] Démontrer le chiffrement d'un message et d'une pièce jointe dans Element, puis inspecter PostgreSQL, les médias et le trafic pour vérifier l'absence de clair.
- [ ] Vérifier le traitement des appareils ajoutés et des clés de chiffrement après révocation ; les copies déjà déchiffrées ne peuvent pas être effacées à distance.
- [ ] Tester explicitement l'enrôlement d'un identifiant non autorisé et les refus attendus.
- [ ] Définir les rôles institutionnels, la séparation des responsabilités et les procédures de récupération de compte.
- [ ] Tester sauvegarde et restauration ; définir supervision, mises à jour et rétention.
- [ ] Préparer un déploiement durci avec TLS et retirer le contournement de validation OIDC utilisé pour le HTTP local.
- [ ] Valider l'interface et les scénarios fonctionnels sur les navigateurs et appareils ciblés.

## Séquence de travail recommandée

1. Répéter le parcours MFA avec un compte agent fictif distinct et vérifier aussi un code incorrect.
2. Créer un salon de démonstration via `kibare_admin.py create-room`, puis échanger un message et un fichier fictifs.
3. Contrôler le contenu stocké dans Synapse/PostgreSQL et les médias, et documenter les limites observées.
4. Révoquer un compte pendant une conversation et vérifier à la fois l'invalidation des sessions et la persistance éventuelle des données déjà reçues localement.
5. Tester une sauvegarde et sa restauration dans un environnement isolé.
6. Ne planifier un déploiement de données réelles qu'après TLS, durcissement, procédures de reprise et revue de sécurité.

Pour les commandes reproductibles, voir [tests/README](../tests/README), [scripts/README.md](../scripts/README.md) et la [note de sécurité](security.md).
