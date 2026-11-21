# Rapport de projet — AutoMind AI

*Assistant conversationnel de recherche automobile — séance de 120 minutes, équipe de 4.*

## 1. Objectif et périmètre

Construire une application de démonstration où un utilisateur décrit en français la voiture qu'il cherche et obtient les annonces correspondantes. Les exigences enrichies ont élargi le périmètre initial dans trois directions :

1. **Interface soignée** : identité visuelle, héros de recherche, indicateurs réels, cartes, état vide, barre latérale.
2. **Chatbot multi-tours** : suivi de contexte, réinitialisation, intentions, avertissements au lieu de suppositions.
3. **Données synthétiques** : 200 annonces fictives reproductibles, validées, avec des fixtures de test déterministes.

**Hors périmètre** (assumé) : IA générative, API externes, vraies photos, base de données, comptes utilisateurs, minimum de prix ou de kilométrage, recherche sur plusieurs villes à la fois.

## 2. Équipe et rôles

| Code | Rôle | Responsabilités principales |
|---|---|---|
| M1 | Chef de projet / documentation | Cadrage, WBS, backlog, planning, suivi, README, rapport, captures |
| M2 | Données et moteur | Catalogue, générateur, validation, filtrage/tri, analyse par règles, multi-tours |
| M3 | Interface | Maquette, Streamlit, cartes, chat, barre latérale, responsive |
| M4 | Qualité | Plan de test, fixtures, tests automatisés, prompts de démo, résultats |

> Remplacer M1–M4 par les noms des membres de l'équipe.

## 3. WBS (organigramme des tâches)

```
AutoMind AI
├── 1. Pilotage (M1)
│   ├── 1.1 Cadrage du besoin (tous)                         P01
│   ├── 1.2 WBS, backlog, affectations                       P02
│   ├── 1.3 Planning et Gantt                                P03
│   └── 1.4 Point d'étape et arbitrages                      P04
├── 2. Données et moteur (M2)
│   ├── 2.1 Référentiel catalogue                       [N]  D01
│   ├── 2.2 Générateur reproductible                    [N]  D02
│   ├── 2.3 Injection fixtures, validation, résumé      [N]  D03
│   ├── 2.4 Filtrage et tri                                  D04
│   ├── 2.5 Analyseur de langage par règles             [N]  D05
│   ├── 2.6 Multi-tours, intentions, réinitialisation   [N]  D06
│   └── 2.7 Régénération finale                         [N]  D08
├── 3. Interface (M3)
│   ├── 3.1 Maquette et notes UI                        [N]  U01
│   ├── 3.2 En-tête, héros, indicateurs                 [N]  U02
│   ├── 3.3 Cartes, critères, état vide                 [N]  U03
│   ├── 3.4 Chat et état de session                     [N]  U04
│   ├── 3.5 Barre latérale, filtres manuels, tri        [N]  U05
│   └── 3.6 Finitions et mobile                         [N]  U06
├── 4. Qualité (M4)
│   ├── 4.1 Plan de test et fixtures                    [N]  Q01
│   ├── 4.2 Tests des 5 scénarios (avant filtrage)           Q02
│   ├── 4.3 Tests du jeu de données                     [N]  Q03
│   ├── 4.4 Tests NLU et multi-tours                    [N]  Q04
│   ├── 4.5 Exécution et consignation                        Q05
│   ├── 4.6 Prompts de démonstration                    [N]  Q06
│   └── 4.7 Non-régression                                   Q07
├── 5. Documentation (M1)
│   ├── 5.1 README                                           P05
│   ├── 5.2 Rapport                                          P06
│   ├── 5.3 Mise à jour finale des documents            [N]  P07
│   └── 5.4 Captures et contrôle des livrables          [N]  P08
├── 6. Intégration (M2 + M3)                                 D07
└── 7. Démonstration (tous)                                  P09
```

`[N]` = travail ajouté par les exigences enrichies.

## 4. Backlog

19 récits utilisateur pour la séance, priorisés selon MoSCoW : 14 Must, 2 Should, 3 Could. Les récits US20–US22 concernent l'itération 2 et US23–US28 l'itération 3 (interface conversationnelle) ([backlog.csv](backlog.csv)). Chaque récit est relié aux tâches du planning et à un critère d'acceptation vérifiable (identifiant de test). Les récits *Could* (filtres manuels, suggestions, historique, statistiques) sont les premiers à sacrifier en cas de retard (§6).

## 5. Planning — 120 minutes

Détail dans [planning.csv](planning.csv) et [gantt.md](gantt.md).

| Phase | Minutes | Contenu |
|---|---|---|
| Cadrage | 0–10 | Tous les membres |
| Fondations | 10–46 | WBS/planning (M1) · catalogue, générateur, validation (M2) · maquette, structure UI (M3) · plan de test, fixtures, **tests des 5 scénarios** (M4) |
| Construction | 46–98 | Filtrage, analyseur, multi-tours (M2) · cartes, chat, barre latérale (M3) · tests données, NLU, démo (M4) · README, rapport (M1) |
| Intégration et recette | 98–115 | Intégration M2+M3, exécution des tests, régénération, finitions, captures |
| Démonstration | 115–120 | Répétition (tous) |

**Contraintes vérifiées par script** (aucun trou ni chevauchement par membre, prédécesseurs respectés) :

- La séance dure **exactement 120 minutes** et chaque membre est occupé de 0 à 120 min.
- **Les tests passent avant le filtrage** : Q01 (plan et fixtures) finit à 30 min, Q02 (tests automatisés T01–T05) à 45 min, et D04 (filtrage) démarre à 46 min. Les tests NLU (Q04, à partir de 58 min) sont écrits en parallèle de l'analyseur (D05, D06), sur le même principe.

Travail ajouté par les exigences enrichies : M1 42 min, M2 83 min, M3 93 min, M4 73 min.

## 6. Arbitrages de temps

Le périmètre enrichi est nettement plus lourd que la version de base, pour une durée inchangée. Pour tenir les 120 minutes, l'équipe a fait les choix suivants, présentés honnêtement :

| Arbitrage | Gain | Contrepartie |
|---|---|---|
| Travail en 4 flux parallèles dès la 10e minute | Tient dans 120 min | **Marge nulle** : tout retard sur le chemin critique D05 → D06 → D07 → P09 décale la démo |
| Analyse par règles plutôt qu'un modèle de langue | Pas de dépendance, résultats explicables et testables | Couverture limitée aux formulations prévues |
| Silhouettes SVG au lieu de photos | Aucune ressource ni réseau | Moins réaliste |
| Seuls les maximums de prix et de kilométrage | Analyse plus simple et plus sûre | « plus de 50 000 km » est signalé, pas appliqué |
| Une seule ville, une seule marque à la fois | Pas d'ambiguïté | « Tunis ou Sfax » demande deux recherches |
| Filtres manuels sans champ « modèle » | Moins de widgets dépendants | Le modèle se précise uniquement dans le chat |
| Tests d'interface sans navigateur (AppTest) | Rapides, automatisables | Le rendu visuel n'est contrôlé que par les captures |
| Rédaction du rapport en parallèle du développement (M1) | Libère la fin de séance | Mise à jour finale nécessaire (P07, 25 min) |

**Plan de repli si retard à 80 min** : abandonner, dans cet ordre, US14 (historique, statistiques), US13 (suggestions), US12 (filtres manuels). Le chemin Must (chat, critères, cartes, état vide, 5 tests) n'est pas touché.

Ce planning est une **prévision** : l'équipe n'a pas mesuré les durées réelles de chaque tâche. Les durées réelles sont à reporter après la séance pour comparer.

## 7. Architecture

```
app.py ──► chatbot.process_message ──► chatbot.parse_message (règles)
  │                 │
  │                 └──► search.filter_cars (comptage)
  ├──► search.filter_cars / sort_cars / suggest_relaxations
  └──► ui.* (HTML/CSS)
generate_cars.py ──► catalog.py + test_fixtures.json ──► cars.json ──► validation.py ──► data_summary.md
```

- **Analyse** : texte normalisé (minuscules, sans accents, longueur conservée), masquage progressif des segments reconnus (modèle, ville…) pour éviter les doubles lectures (« Série 3 » n'est pas un prix, « Peugeot 2008 » n'est pas une année), classification des nombres selon l'unité, le mot-clé le plus proche et le comparateur.
- **Dialogue** : `Turn` structuré (intent, criteria, extracted, added/changed/removed, warnings, explanation, response, result_count, sort). Depuis l'itération 3, les critères précédents sont **conservés par défaut** : un message ajoute, remplace ou retire des critères. Seule une demande explicite (« nouvelle recherche ») repart de zéro.
- **Intentions** : search, follow_up, sort (préférence d'ordre sans nouveau critère), reset, no_criteria, ambiguous, unsupported, help.
- **Interface** (itération 3) : une seule page de conversation. Chaque action (message tapé, suggestion, puce, « Voir les détails ») est mise en file puis traitée avec un indicateur « Je recherche… ». La réponse est enregistrée avec les identifiants **réels** des véhicules trouvés et affichée sous forme de cartes dans le message. Les filtres manuels (optionnels) publient leur résultat dans le chat.

## 8. Données

- `generate_cars.py --count 200 --seed 42` : 12 fixtures et 188 annonces tirées au hasard, 17 marques, 54 modèles, 10 villes, 4 énergies, années 2012–2025.
- Cohérence : couples marque-modèle et carburants issus du catalogue, kilométrage = âge × kilométrage annuel selon l'énergie, prix = prix neuf fictif × 0,92^âge × facteurs (kilométrage, énergie, boîte, état) × bruit, électriques en boîte automatique et postérieurs à 2018.
- Plausibilité mesurée : prix moyen premium 106 333 DT contre 47 046 DT pour les généralistes ; 171 763 km en moyenne avant 2017 contre 34 830 km à partir de 2022 ([data_summary.md](../data_summary.md)).
- **Prix fictifs** : ce ne sont pas des valeurs du marché.

## 9. Tests

- Plan : 50 cas ([test_plan.csv](../testing/test_plan.csv)), dont les 5 scénarios obligatoires T01–T05 exécutés sur `test_fixtures.json` pour des résultats stables.
- Exécution : `python -m pytest -v` donne **134 tests réussis, 0 échec** le 2026-11-21. Le détail par test, avec les identifiants observés pour T01–T05, est dans [test_results.csv](../testing/test_results.csv), généré depuis le rapport JUnit de cette exécution. La synthèse se trouve dans [rapport_tests.md](../testing/rapport_tests.md).
- Défauts trouvés pendant les tests et corrigés :
  - L'hypothèse d'un test de suggestions était fausse : aucune relaxation simple ne trouvait de résultat. Le test a été corrigé et vérifie désormais aussi qu'aucune suggestion n'est inventée.
  - Des modèles du catalogue étaient absents de la base générée (ex. Mercedes Classe A) : ils étaient ignorés sans explication. Un avertissement a été ajouté.
  - Le planning comportait deux dépendances incohérentes (D02 ← Q01 et Q03 ← D03). Elles ont été corrigées après vérification automatique.

### Itération 2 — expérience du chatbot

Après la séance de 120 minutes, une seconde itération a amélioré l'expérience conversationnelle. Ce travail n'est **pas** compté dans le planning de 120 minutes : l'y ajouter aurait demandé de supprimer d'autres tâches, alors que la marge était déjà nulle. Il est suivi à part dans le backlog (US20 à US22).

| Tâche | Responsable | Livrable | Vérification |
|---|---|---|---|
| I2-U1 Compositeur de chat, en-tête, bulles titrées et horodatées, aperçu des résultats | M3 | app.py, ui.py | U04 |
| I2-D1 Réponses rapides calculées sur les données, repères des cartes | M2 | search.py | C01, C02, C04 |
| I2-U2 Puces ✕ de retrait, ✓ sur les cartes, synthèse des prix | M3 | app.py, ui.py | C03, U05 |
| I2-Q1 Nouveaux cas de test, exécution, rapport de tests, contrôle visuel | M4 | test_plan.csv, rapport_tests.md | 106/106 (à cette date) |

Les durées de cette itération n'ont pas été mesurées.


### Itération 3 — refonte en interface conversationnelle

L'application passe d'une page « recherche + panneau de résultats » à **une seule conversation** : les cartes véhicules, les critères, les relances, les pistes en cas d'absence de résultat et les fiches détaillées sont des **messages de l'assistant**. Comme l'itération 2, ce travail est hors du planning de 120 minutes et suivi à part (US23–US28). Ses durées n'ont pas été mesurées.

| Tâche | Responsable | Livrable | Vérification |
|---|---|---|---|
| I3-A Analyse de l'existant et plan de refonte | M1 + M3 | — | — |
| I3-D1 Contexte conservé par défaut, valeurs multiples, retrait par valeur, tri en langage naturel, phrases naturelles | M2 | chatbot.py | R01–R08 |
| I3-D2 Comparaison pour la fiche, pistes d'élargissement reformulées | M2 | search.py | R09, T22 |
| I3-U1 Page unique : accueil, messages, saisie fixée, indicateur de traitement, défilement | M3 | app.py, ui.py | U01, U09 |
| I3-U2 Cartes en carrousel dans les réponses, puces cliquables, relance, fiche détaillée | M3 | app.py, ui.py | U02–U08, U10 |
| I3-Q1 Plan de test (50 cas), 134 tests, contrôle dans Chrome, rapport de tests | M4 | test_plan.csv, rapport_tests.md | 134/134 |

Changement de règle assumé : dans l'itération 1, « Je cherche une Renault » après une recherche diesel démarrait une nouvelle recherche. Désormais, le contexte est **conservé par défaut** (Renault s'ajoute à Diesel), comme le demandent les nouvelles exigences. Seule une demande explicite (« nouvelle recherche ») repart de zéro. De même, « pas chère » ne produit plus un simple avertissement : la demande **trie les résultats par prix** sans inventer de budget. Les tests correspondants (T18, R02) ont été mis à jour.

## 10. Risques

| Risque | Prob. | Impact | Parade |
|---|---|---|---|
| Retard sur l'analyseur (chemin critique) | Moyenne | Élevé | Tests Q04 prêts d'avance ; repli sur les Must (§6) |
| Formulation non prévue pendant la démo | Élevée | Moyen | Avertissements explicites, exemples cliquables, scénario répété |
| Sélecteurs CSS Streamlit changeants | Faible | Moyen | Version testée (1.56) indiquée ; l'application reste fonctionnelle sans CSS |
| Données jugées irréalistes | Faible | Faible | Avertissement « fictif » partout, contrôles de plausibilité |
| Panne réseau pendant la démo | Faible | Nul | Aucune dépendance réseau |

## 11. Bilan

Les critères d'acceptation sont couverts : interface moderne et cohérente (captures dans `screenshots/`, prises sur l'application réellement lancée), chatbot multi-tours avec réinitialisation et gestion prudente des ambiguïtés, 200 annonces reproductibles et validées, 5 scénarios obligatoires et 129 autres tests exécutés (134 au total), planning de 120 minutes qui intègre le nouveau travail et respecte la contrainte « tests avant filtrage ».

Pistes d'amélioration : minimum de prix et de kilométrage, plusieurs villes, tolérance aux fautes de frappe (distance d'édition), mesure des durées réelles de la séance.
