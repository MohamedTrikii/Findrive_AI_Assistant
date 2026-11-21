# Résumé du jeu de données — AutoMind AI

> **Données synthétiques et fictives.** Les prix sont générés par un modèle simple (prix neuf fictif, décote annuelle, kilométrage, état) et **ne constituent pas une cote du marché tunisien**.

Fichier généré automatiquement par `automind/generate_cars.py` — ne pas éditer à la main.

## Génération

- Commande : `python -m automind.generate_cars --count 200 --seed 42`
- Graine aléatoire : `42` (même graine = même fichier)
- Année de référence : 2026
- Annonces : 200 dont 12 annonces de test fixes (`FIX-xxx`, issues de `data/test_fixtures.json`)

## Validation

**✅ Validation réussie — aucune erreur**

Contrôles : identifiants uniques · aucune annonce dupliquée · champs obligatoires présents · marque connue · modèle valide pour la marque · catégorie et carburant cohérents avec le modèle · année entre 2012 et 2025 · prix > 0 · kilométrage > 0 · ville, carburant, catégorie, boîte et état dans les listes autorisées · électrique ⇒ boîte automatique.

## Chiffres clés

| Indicateur | Valeur |
|---|---:|
| Total véhicules | 200 |
| Marques | 17 |
| Modèles distincts | 54 |
| Villes | 10 |
| Prix minimum | 12 000 DT |
| Prix maximum | 191 500 DT |
| Prix moyen | 51 492 DT |
| Kilométrage minimum | 7 500 km |
| Kilométrage maximum | 364 500 km |
| Kilométrage moyen | 96 492 km |
| Années | 2012 – 2025 |

## Contrôles de plausibilité

| Contrôle | Valeur |
|---|---:|
| Prix moyen marques premium (Audi, BMW, Mercedes) | 106 333 DT |
| Prix moyen marques généralistes | 47 046 DT |
| Kilométrage moyen des véhicules ≤ 2016 | 171 763 km |
| Kilométrage moyen des véhicules ≥ 2022 | 34 830 km |

## Répartitions

| Carburant | Annonces | Part |
|---|---:|---:|
| Essence | 119 | 59.5 % |
| Diesel | 59 | 29.5 % |
| Hybride | 11 | 5.5 % |
| Électrique | 11 | 5.5 % |

| Catégorie | Annonces | Part |
|---|---:|---:|
| SUV | 67 | 33.5 % |
| Citadine | 63 | 31.5 % |
| Berline | 35 | 17.5 % |
| Compacte | 35 | 17.5 % |

| Boîte | Annonces | Part |
|---|---:|---:|
| Manuelle | 129 | 64.5 % |
| Automatique | 71 | 35.5 % |

| Ville | Annonces | Part |
|---|---:|---:|
| Tunis | 46 | 23.0 % |
| Ariana | 30 | 15.0 % |
| Sfax | 23 | 11.5 % |
| Nabeul | 20 | 10.0 % |
| Sousse | 17 | 8.5 % |
| Bizerte | 16 | 8.0 % |
| Monastir | 14 | 7.0 % |
| Mahdia | 13 | 6.5 % |
| Kairouan | 12 | 6.0 % |
| Gabès | 9 | 4.5 % |

| Marque | Annonces | Part |
|---|---:|---:|
| Peugeot | 33 | 16.5 % |
| Hyundai | 22 | 11.0 % |
| Renault | 19 | 9.5 % |
| Toyota | 14 | 7.0 % |
| Kia | 13 | 6.5 % |
| Citroën | 12 | 6.0 % |
| Seat | 12 | 6.0 % |
| Volkswagen | 12 | 6.0 % |
| Nissan | 11 | 5.5 % |
| Dacia | 9 | 4.5 % |
| Ford | 9 | 4.5 % |
| BMW | 8 | 4.0 % |
| Fiat | 8 | 4.0 % |
| Mercedes | 6 | 3.0 % |
| Skoda | 6 | 3.0 % |
| Opel | 5 | 2.5 % |
| Audi | 1 | 0.5 % |

