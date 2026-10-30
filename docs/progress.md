# État d'avancement de Kibare

## 1. Présentation

Kibare est actuellement au stade de prototype technique. Le projet vise à mettre en place une plateforme de messagerie instantanée reposant sur Matrix, avec une infrastructure auto-hébergeable et adaptée aux besoins des institutions burkinabè.

Ce document présente l'état d'avancement du projet et les principales évolutions prévues.

## 2. Fonctionnalités et composants réalisés

Les éléments suivants ont été mis en place :

- [x] Mise en place de l'environnement Docker Compose.
- [x] Configuration du serveur Matrix Synapse.
- [x] Intégration de PostgreSQL comme base de données.
- [x] Intégration du client web Element.
- [x] Configuration d'Element pour utiliser le serveur Matrix de Kibare.
- [x] Persistance des données PostgreSQL dans un volume Docker.
- [x] Externalisation du mot de passe PostgreSQL dans un fichier `.env`.
- [x] Mise en place des règles `.gitignore` pour exclure les fichiers sensibles et les données générées.
- [x] Documentation initiale de l'architecture et des principes de sécurité.

## 3. Éléments en cours de validation

Les aspects suivants nécessitent encore des tests et une validation approfondie :

- [ ] Vérification complète des échanges entre Element et Synapse.
- [ ] Validation des mécanismes d'authentification et de gestion des sessions.
- [ ] Tests du chiffrement de bout en bout dans les salons compatibles.
- [ ] Vérification des procédures de sauvegarde et de restauration.
- [ ] Tests de fonctionnement après redémarrage des conteneurs.

## 4. Fonctionnalités à développer

Les évolutions envisagées comprennent :

- [ ] Gestion avancée des identités et des comptes utilisateurs.
- [ ] Gestion des rôles et des permissions.
- [ ] Révocation des sessions et gestion des appareils.
- [ ] Mise en place d'une interface d'administration adaptée.
- [ ] Notifications et amélioration de l'expérience utilisateur.
- [ ] Mise en place d'une configuration de déploiement avec HTTPS et reverse proxy.
- [ ] Renforcement de la supervision et de la journalisation.
- [ ] Élaboration d'une stratégie de sauvegarde et de reprise après incident.

## 5. Prochaines étapes prioritaires

Les prochaines étapes de développement sont organisées autour de quatre axes :

1. **Validation technique** : vérifier le fonctionnement global des services et des échanges Matrix.
2. **Sécurité** : tester les mécanismes d'authentification, les sessions et le chiffrement.
3. **Administration** : concevoir les mécanismes de gestion des utilisateurs, des rôles et des accès.
4. **Préparation au déploiement** : définir une architecture réseau adaptée à un environnement institutionnel.

## 6. Conclusion

Le socle technique de Kibare est en place. Les prochaines phases porteront principalement sur la validation fonctionnelle, le renforcement de la sécurité et le développement des fonctionnalités nécessaires à une exploitation institutionnelle.

L'évolution du projet sera documentée au fur et à mesure de l'avancement des travaux.
