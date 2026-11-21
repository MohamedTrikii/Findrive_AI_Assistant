"""Validation et statistiques du jeu de données AutoMind AI."""

from __future__ import annotations

from collections import Counter
from statistics import mean

from .catalog import (
    BRANDS,
    CATEGORIES,
    CITIES,
    CONDITIONS,
    FUELS,
    MIN_YEAR,
    PREMIUM_BRANDS,
    REFERENCE_YEAR,
    REQUIRED_FIELDS,
    TRANSMISSIONS,
    models_of,
)


def _signature(car: dict) -> tuple:
    """Identité d'une annonce hors identifiant (détection des doublons)."""
    return tuple(car.get(f) for f in REQUIRED_FIELDS if f not in ("id", "source"))


def validate_cars(cars: list[dict]) -> list[str]:
    """Retourne la liste des erreurs (vide si le jeu de données est valide)."""
    errors: list[str] = []
    if not cars:
        return ["Le jeu de données est vide."]

    ids = Counter(c.get("id") for c in cars)
    for car_id, n in ids.items():
        if n > 1:
            errors.append(f"Identifiant dupliqué : {car_id} ({n} fois)")

    signatures = Counter(_signature(c) for c in cars)
    for sig, n in signatures.items():
        if n > 1:
            errors.append(f"Annonce dupliquée ({n} fois) : {sig[:3]}")

    for i, car in enumerate(cars):
        ref = car.get("id", f"#{i}")
        missing = [f for f in REQUIRED_FIELDS if car.get(f) in (None, "")]
        if missing:
            errors.append(f"{ref} : champs manquants {missing}")
            continue
        brand, model = car["marque"], car["modele"]
        if brand not in BRANDS:
            errors.append(f"{ref} : marque inconnue « {brand} »")
        elif model not in models_of(brand):
            errors.append(f"{ref} : modèle « {model} » invalide pour {brand}")
        else:
            category, _, fuels = models_of(brand)[model]
            if car["categorie"] != category:
                errors.append(f"{ref} : catégorie {car['categorie']} incohérente pour {brand} {model}")
            if car["carburant"] not in fuels:
                errors.append(f"{ref} : carburant {car['carburant']} impossible pour {brand} {model}")
        if not isinstance(car["annee"], int) or not MIN_YEAR <= car["annee"] < REFERENCE_YEAR:
            errors.append(f"{ref} : année invalide {car['annee']}")
        if not isinstance(car["prix"], int) or car["prix"] <= 0:
            errors.append(f"{ref} : prix invalide {car['prix']}")
        if not isinstance(car["kilometrage"], int) or car["kilometrage"] <= 0:
            errors.append(f"{ref} : kilométrage invalide {car['kilometrage']}")
        if car["ville"] not in CITIES:
            errors.append(f"{ref} : ville inconnue « {car['ville']} »")
        if car["carburant"] not in FUELS:
            errors.append(f"{ref} : carburant inconnu « {car['carburant']} »")
        if car["categorie"] not in CATEGORIES:
            errors.append(f"{ref} : catégorie inconnue « {car['categorie']} »")
        if car["boite"] not in TRANSMISSIONS:
            errors.append(f"{ref} : boîte inconnue « {car['boite']} »")
        if car["etat"] not in CONDITIONS:
            errors.append(f"{ref} : état inconnu « {car['etat']} »")
        if car["carburant"] == "Électrique" and car["boite"] != "Automatique":
            errors.append(f"{ref} : un véhicule électrique doit être automatique")
    return errors


def summarize(cars: list[dict]) -> dict:
    prices = [c["prix"] for c in cars]
    kms = [c["kilometrage"] for c in cars]
    years = [c["annee"] for c in cars]
    by_brand = Counter(c["marque"] for c in cars)
    premium = [c["prix"] for c in cars if c["marque"] in PREMIUM_BRANDS]
    generalist = [c["prix"] for c in cars if c["marque"] not in PREMIUM_BRANDS]
    old = [c["kilometrage"] for c in cars if c["annee"] <= 2016]
    recent = [c["kilometrage"] for c in cars if c["annee"] >= 2022]
    return {
        "total": len(cars),
        "fixtures": sum(1 for c in cars if c.get("source") == "fixture"),
        "brands": dict(sorted(by_brand.items(), key=lambda kv: (-kv[1], kv[0]))),
        "brand_count": len(by_brand),
        "model_count": len({(c["marque"], c["modele"]) for c in cars}),
        "cities": dict(Counter(c["ville"] for c in cars).most_common()),
        "city_count": len({c["ville"] for c in cars}),
        "fuels": dict(Counter(c["carburant"] for c in cars).most_common()),
        "categories": dict(Counter(c["categorie"] for c in cars).most_common()),
        "transmissions": dict(Counter(c["boite"] for c in cars).most_common()),
        "conditions": {k: v for k, v in Counter(c["etat"] for c in cars).items()},
        "price_min": min(prices), "price_max": max(prices), "price_avg": round(mean(prices)),
        "km_min": min(kms), "km_max": max(kms), "km_avg": round(mean(kms)),
        "year_min": min(years), "year_max": max(years),
        "premium_avg_price": round(mean(premium)) if premium else None,
        "generalist_avg_price": round(mean(generalist)) if generalist else None,
        "old_avg_km": round(mean(old)) if old else None,
        "recent_avg_km": round(mean(recent)) if recent else None,
    }


def _n(x: int | None) -> str:
    return "—" if x is None else f"{x:,}".replace(",", " ")


def _table(title: str, counts: dict, total: int) -> list[str]:
    lines = [f"| {title} | Annonces | Part |", "|---|---:|---:|"]
    for k, v in counts.items():
        lines.append(f"| {k} | {v} | {100 * v / total:.1f} % |")
    return lines + [""]


def summary_markdown(cars: list[dict], metadata: dict, errors: list[str]) -> str:
    s = summarize(cars)
    t = s["total"]
    status = "✅ Validation réussie — aucune erreur" if not errors else f"❌ {len(errors)} erreur(s)"
    lines = [
        "# Résumé du jeu de données — AutoMind AI",
        "",
        "> **Données synthétiques et fictives.** Les prix sont générés par un modèle simple"
        " (prix neuf fictif, décote annuelle, kilométrage, état) et **ne constituent pas une"
        " cote du marché tunisien**.",
        "",
        "Fichier généré automatiquement par `automind/generate_cars.py` — ne pas éditer à la main.",
        "",
        "## Génération",
        "",
        f"- Commande : `python -m automind.generate_cars --count {metadata.get('count')} --seed {metadata.get('seed')}`",
        f"- Graine aléatoire : `{metadata.get('seed')}` (même graine = même fichier)",
        f"- Année de référence : {metadata.get('reference_year')}",
        f"- Annonces : {t} dont {s['fixtures']} annonces de test fixes (`FIX-xxx`, issues de `data/test_fixtures.json`)",
        "",
        "## Validation",
        "",
        f"**{status}**",
        "",
        "Contrôles : identifiants uniques · aucune annonce dupliquée · champs obligatoires présents ·"
        " marque connue · modèle valide pour la marque · catégorie et carburant cohérents avec le modèle ·"
        f" année entre {MIN_YEAR} et {REFERENCE_YEAR - 1} · prix > 0 · kilométrage > 0 · ville, carburant,"
        " catégorie, boîte et état dans les listes autorisées · électrique ⇒ boîte automatique.",
        "",
    ]
    if errors:
        lines += ["```", *errors[:50], "```", ""]
    lines += [
        "## Chiffres clés",
        "",
        "| Indicateur | Valeur |",
        "|---|---:|",
        f"| Total véhicules | {t} |",
        f"| Marques | {s['brand_count']} |",
        f"| Modèles distincts | {s['model_count']} |",
        f"| Villes | {s['city_count']} |",
        f"| Prix minimum | {_n(s['price_min'])} DT |",
        f"| Prix maximum | {_n(s['price_max'])} DT |",
        f"| Prix moyen | {_n(s['price_avg'])} DT |",
        f"| Kilométrage minimum | {_n(s['km_min'])} km |",
        f"| Kilométrage maximum | {_n(s['km_max'])} km |",
        f"| Kilométrage moyen | {_n(s['km_avg'])} km |",
        f"| Années | {s['year_min']} – {s['year_max']} |",
        "",
        "## Contrôles de plausibilité",
        "",
        "| Contrôle | Valeur |",
        "|---|---:|",
        f"| Prix moyen marques premium ({', '.join(PREMIUM_BRANDS)}) | {_n(s['premium_avg_price'])} DT |",
        f"| Prix moyen marques généralistes | {_n(s['generalist_avg_price'])} DT |",
        f"| Kilométrage moyen des véhicules ≤ 2016 | {_n(s['old_avg_km'])} km |",
        f"| Kilométrage moyen des véhicules ≥ 2022 | {_n(s['recent_avg_km'])} km |",
        "",
        "## Répartitions",
        "",
        *_table("Carburant", s["fuels"], t),
        *_table("Catégorie", s["categories"], t),
        *_table("Boîte", s["transmissions"], t),
        *_table("Ville", s["cities"], t),
        *_table("Marque", s["brands"], t),
    ]
    return "\n".join(lines)
