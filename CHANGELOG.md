# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versionnage [SemVer](https://semver.org/lang/fr/).

## [Non publié]

## [1.1.0] — 2026-11-22

### Ajouté
- Identité visuelle **Findrive Assistant** : logo dans l'onglet, l'en-tête et la barre latérale ; bannière du README.
- Dépôt GitHub renommé en `Findrive_AI_Assistant`.
- Guide de contribution, politique de sécurité, modèles d'issue et de Pull Request, Dependabot.
- Feuille de route dans le README.

### Modifié
- Le produit s'appelle désormais **Findrive Assistant** (anciennement AutoMind AI).
- Package Python renommé de `automind` en `findrive` ; distribution `findrive-assistant`.

## [1.0.0] — 2026-11-21

### Ajouté
- Assistant conversationnel de recherche automobile (Streamlit), résultats affichés dans la conversation.
- Moteur d'analyse par règles : villes, carburants, marques, modèles, prix, kilométrage, année, catégorie, boîte ; dialogue multi-tours, retrait et remplacement de critères.
- Jeu de 200 annonces fictives reproductible (graine 42) avec validation automatique.
- Suite de tests principale (188 tests) et campagne QA formelle (70 cas, dont tests navigateur Playwright).
- Intégration continue GitHub Actions (lint Ruff, tests Python 3.10 → 3.13, campagne QA).
- Dockerfile, `pyproject.toml`, licence MIT.

### Modifié
- Code réorganisé en package `automind/` ; données dans `data/`, tests dans `tests/`, documentation dans `docs/`, scripts dans `scripts/`.
- « moins de », « inférieur à », « sous » deviennent des bornes strictes ; prise en charge du prix minimum.

[Non publié]: https://github.com/MohamedTrikii/Findrive_AI_Assistant/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/MohamedTrikii/Findrive_AI_Assistant/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/MohamedTrikii/Findrive_AI_Assistant/releases/tag/v1.0.0
