# Rapport de tests — Findrive Assistant (interface conversationnelle)

| | |
|---|---|
| Date d'exécution | 2026-11-21 |
| Commande | `python -m pytest -v` (ou `scripts\lancer.bat tests`) |
| Environnement | Windows 11 · Python 3.13.11 · Streamlit 1.56.0 · pytest 9.0.2 |
| Résultat global | **134 tests exécutés · 134 réussis · 0 échec · 0 ignoré** (≈ 10 s) |
| Plan de test | [test_plan.csv](test_plan.csv) : 50 cas |
| Résultats détaillés | [test_results.csv](test_results.csv) : 1 ligne par test, générée depuis le rapport JUnit de l'exécution |

> **Mise à jour (2026-11-21, campagne QA [qa/](../../qa/))** : ce rapport décrit l'exécution de 134 tests avant correction. Depuis, « moins de » / « inférieur à » / « sous » sont des bornes **strictes** (« maximum », « jusqu'à »… restent inclusives) et le prix minimum est géré. Les résultats observés T02, T03, T04 et U06 ci-dessous ne sont plus d'actualité (FIX-008 à 40 000 DT est désormais exclu par « moins de 40 000 DT ») ; la suite d'origine compte maintenant 140 tests, tous réussis. Résultats bruts : [qa/results/](../../qa/results/).

Chaque test est rattaché à un cas du plan, sauf 10 tests « complémentaires » sur des détails internes. Un cas peut regrouper plusieurs tests : par exemple, R06 vérifie 9 formulations de tri.

## 1. Les 5 scénarios fonctionnels obligatoires

Exécutés sur [test_fixtures.json](../../data/test_fixtures.json) (12 véhicules fixes) pour des résultats stables.

| ID | Message | Résultat attendu | Résultat observé | Statut |
|---|---|---|---|---|
| T01 | `voiture à Tunis` | FIX-001, 002, 005, 006, 007, 008 | `{'ville': 'Tunis'}` → FIX-001, 002, 005, 006, 007, 008 | ✅ |
| T02 | `diesel moins de 40000 DT` | FIX-001, 002, 008 | `{'carburant': 'Diesel', 'prix_max': 40000}` → FIX-001, 002, 008 | ✅ |
| T03 | `moins de 40 000 DT` | FIX-001, 002, 004, 005, 008 | `{'prix_max': 40000}` → FIX-001, 002, 004, 005, 008 | ✅ |
| T04 | `diesel à Tunis moins de 40000 DT et moins de 100000 km` | 4 critères → FIX-001, 002, 008 | 4 critères → FIX-001, 002, 008 | ✅ |
| T05 | `diesel à Sousse moins de 30000 DT` | 0 résultat + « Je n'ai trouvé aucune voiture correspondant exactement à ces critères. On peut essayer d'élargir la recherche. » | 0 résultat, message affiché | ✅ |

## 2. Nouveaux tests de l'interface conversationnelle

### Moteur conversationnel (R01–R09)

| ID | Cas | Tests | Valeur observée / point vérifié | Statut |
|---|---|---:|---|---|
| R01 | Conversation de la consigne : diesel → budget → « plus récents » | 1 | `{ville, carburant}` → `+ prix_max 40000` → tri « Année la plus récente » ; réponse « D'accord, je limite la recherche à 40 000 DT. J'ai maintenant 3 voitures diesel à Tunis jusqu'à 40 000 DT. » | ✅ |
| R02 | Contexte conservé par défaut · « nouvelle recherche » repart de zéro | 2 | diesel puis Peugeot → Diesel **et** Peugeot | ✅ |
| R03 | Plusieurs marques, villes ou carburants | 2 | `{'marque': ['Peugeot', 'Renault'], 'prix_max': 40000}` → FIX-001, 002, 008 | ✅ |
| R04 | « Enlève Renault », « Enlève le critère diesel », critère absent signalé | 3 | seule la valeur citée est retirée | ✅ |
| R05 | « Augmente le budget à 50 000 DT » · « augmente le budget » sans montant | 2 | 40 000 → 50 000 DT · sans montant : question, rien n'est modifié | ✅ |
| R06 | 9 formulations de tri (« plus récents », « moins cher », « économique »…) + tri avec critère | 10 | un tri ne modifie jamais les critères | ✅ |
| R07 | Demande complète de la consigne (automatique, Sfax, 50 000 DT, 100 000 km) | 1 | 4 critères reconnus | ✅ |
| R08 | Phrase naturelle des résultats | 1 | « voitures diesel à Sfax jusqu'à 40 000 DT » | ✅ |
| R09 | Comparaison dans la fiche détaillée | 1 | prix, km, année comparés aux autres résultats | ✅ |

### Interface (U01–U10, Streamlit AppTest)

Les résultats affichés dans le chat sont comparés à une recherche indépendante faite sur `cars.json` : **aucun résultat n'est codé en dur**.

| ID | Cas | Statut |
|---|---|---|
| U01 | Écran d'accueil (titre + 4 cartes) · clic sur une suggestion → résultats réels dans le chat · l'accueil disparaît | ✅ |
| U02 | Résultats dans chaque réponse · suivi « Budget maximum 40 000 dinars » · identifiants = recherche indépendante | ✅ |
| U03 | « Montre-moi des modèles plus récents » → cartes triées par année décroissante | ✅ |
| U04 | Question « prix, kilométrage ou année ? » → clic tracé dans la conversation | ✅ |
| U05 | « Voir les détails » → fiche dans la conversation · fermeture → retour au fil | ✅ |
| U06 | Puces « Peugeot ✕ », « Renault ✕ », « Budget ≤ 40 000 DT ✕ » · clic → seule la valeur visée est retirée | ✅ |
| U07 | Aucun résultat → message + pistes · la piste choisie donne des résultats | ✅ |
| U08 | « Afficher plus » ajoute 6 cartes dans la même réponse (aucune page séparée) | ✅ |
| U09 | « Nouvelle conversation » → accueil réaffiché, critères effacés | ✅ |
| U10 | Filtres manuels (optionnels) → résultat publié comme message dans le chat | ✅ |

## 3. Tous les cas du plan

| Groupe | Cas | Tests | Statut |
|---|---|---:|---|
| Scénarios obligatoires | T01–T05 | 5 | ✅ |
| Compréhension (prix, km, villes, carburants, années, marque/modèle) | T06–T13 | 35 | ✅ |
| Conversation et robustesse | T14–T22 | 16 | ✅ |
| Affinage, puces, repères | C01–C04 | 13 | ✅ |
| Moteur conversationnel | R01–R09 | 23 | ✅ |
| Données (reproductibilité, validation, plausibilité, prompts de démo) | D01–D05 | 22 | ✅ |
| Interface | U01–U10 | 10 | ✅ |
| Complémentaires | — | 10 | ✅ |
| **Total** | **50 cas** | **134** | **134 ✅** |

## 4. Contrôle dans un vrai navigateur

L'application a été lancée (`streamlit run app.py`) et pilotée avec Playwright dans Chrome, en 1280 px et en 390 px (mobile). Aucune erreur JavaScript n'a été relevée sur la page, et 11 animations CSS distinctes ont été mesurées en cours d'exécution (`document.getAnimations()`). Les captures sont dans [screenshots/](../screenshots/).

| Capture | Ce qui est vérifié |
|---|---|
| `01_accueil_anime.png` | Bandeau d'accueil animé (halos, titre dégradé, voitures qui roulent), 4 suggestions, barre du haut en verre dépoli |
| `02_accueil_survol_suggestion.png` | Survol d'une suggestion : carte soulevée, halo et flèche |
| `03_chargement.png` | Indicateur de recherche : voiture sur la piste + cartes « fantômes » scintillantes |
| `04_resultats_dans_le_chat.png` | Cartes en carrousel **dans** la réponse, puces 🔎 cliquables, relance, pistes d'affinage |
| `05_survol_carte.png` | Survol d'une carte : soulèvement, reflet, voiture qui avance, roues qui tournent |
| `06_fiche_detaillee.png` | Fiche dans la conversation (voiture qui arrive, caractéristiques en cascade), comparaison, retour |
| `07_aucun_resultat.png` | État vide animé + piste « Supprimer le critère de carburant · 3 » |
| `08_mobile_accueil.png`, `09_mobile_resultats.png` | Mobile : accueil sur un seul écran, carrousel à faire défiler au doigt |

Vérifications faites uniquement dans le navigateur :

- **Un clic sur « Voir les détails » dans une réponse ancienne ouvre la bonne fiche.** Test : 1re réponse → Dacia Sandero AM-0034.
- **« Fermer la fiche » retire la fiche et la demande associée**, sans déclencher d'autre action.

## 5. Défauts trouvés pendant cette itération

| # | Défaut | Détecté par | Correction |
|---|---|---|---|
| 1 | Cartes du carrousel superposées (règle `flex: 1 1 128px` imposée par Streamlit) | Capture d'écran | Largeur fixe sur l'enveloppe `stLayoutWrapper` |
| 2 | Bouton « Nouvelle conversation » sur deux lignes | Capture d'écran | Texte sur une ligne, colonne élargie |
| 3 | `st.components.v1.html` obsolète dans Streamlit 1.56 | Avertissement à l'exécution | Remplacé par `st.iframe` |
| 4 | Phrase « Plus récente que 0 des 2 autres voitures » | Capture d'écran | Formulations dédiées (« Parmi les plus anciennes… ») |
| 5 | « Parfait ! » suivi de « aucune voiture trouvée » | Valeur observée de T05 | « J'ai bien compris votre recherche. » quand il n'y a aucun résultat |
| 6 | Puces de changements redondantes pour une nouvelle recherche | Capture d'écran | Affichées seulement lors d'une modification |

## 6. Limites connues

- **AppTest** (tests d'interface sans navigateur) attribue parfois un clic sur un bouton d'une réponse *ancienne* à un autre bouton, quand l'arbre des widgets a changé. Le même parcours fonctionne dans Chrome (§4). Les tests automatiques cliquent donc sur la dernière réponse, et le test U05 vérifie seulement que la fiche a disparu après fermeture.
- La compréhension reste **par règles** : une formulation inédite peut ne pas être reconnue. Dans ce cas, elle est signalée et jamais devinée.
- L'indicateur « Je recherche… » reste affiché au moins 0,55 s. La recherche elle-même prend quelques millisecondes ; ce délai sert seulement à rendre l'indicateur perceptible.
- Images des véhicules : illustrations SVG générées (silhouette selon la catégorie, couleur selon la référence), pas de vraies photos.
- Les règles CSS s'appuient sur des sélecteurs internes de Streamlit (`stLayoutWrapper`, `stChatMessageAvatarUser`…), vérifiés avec Streamlit 1.56.
