"""Chargement des données, filtrage, tri, statistiques et suggestions."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

TEXT_KEYS = ("marque", "modele", "ville", "carburant", "categorie", "boite")

SORT_OPTIONS = {
    "Prix croissant": (lambda c: (c["prix"], c["kilometrage"]), False),
    "Prix décroissant": (lambda c: (c["prix"], -c["kilometrage"]), True),
    "Kilométrage croissant": (lambda c: (c["kilometrage"], c["prix"]), False),
    "Année la plus récente": (lambda c: (c["annee"], -c["prix"]), True),
}
DEFAULT_SORT = "Prix croissant"


def load_dataset(path: str | Path) -> tuple[list[dict], dict]:
    """Lit cars.json (objet {metadata, cars} ou simple liste)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, {}
    return data["cars"], data.get("metadata", {})


# Bornes numériques : clé de critère -> (champ de l'annonce, sens). Un indicateur « <clé>_strict » = True
# rend la borne stricte (« moins de 40 000 DT » exclut 40 000 DT) ; sinon elle est inclusive
# (« maximum 40 000 DT », « jusqu'à 40 000 DT » acceptent 40 000 DT).
NUMERIC_BOUNDS = {
    "prix_max": ("prix", "max"),
    "prix_min": ("prix", "min"),
    "kilometrage_max": ("kilometrage", "max"),
    "kilometrage_min": ("kilometrage", "min"),
    "annee_min": ("annee", "min"),
    "annee_max": ("annee", "max"),
}
REQUIRED_TEXT = ("id", "marque", "modele", "ville", "carburant")
REQUIRED_NUMBERS = ("prix", "kilometrage", "annee")


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_valid_record(car) -> bool:
    """Annonce exploitable : objet, champs texte non vides, prix/kilométrage/année numériques et positifs."""
    if not isinstance(car, dict):
        return False
    if any(not isinstance(car.get(k), str) or not car.get(k).strip() for k in REQUIRED_TEXT):
        return False
    return all(_is_number(car.get(k)) and car.get(k) >= 0 for k in REQUIRED_NUMBERS)


def clean_records(cars) -> tuple[list[dict], int]:
    """Écarte les annonces mal formées (champ manquant, valeur nulle ou non numérique) au lieu de planter."""
    if not isinstance(cars, list):
        raise TypeError("la clé « cars » doit contenir une liste d'annonces")
    valid = [c for c in cars if is_valid_record(c)]
    return valid, len(cars) - len(valid)


def matches(car: dict, criteria: dict) -> bool:
    if not isinstance(car, dict):
        return False
    for key in TEXT_KEYS:
        wanted = criteria.get(key)
        if wanted is None:
            continue
        options = wanted if isinstance(wanted, (list, tuple)) else [wanted]  # « Peugeot ou Renault »
        if car.get(key) is None or str(car[key]).casefold() not in {str(o).casefold() for o in options}:
            return False
    for key, (field, side) in NUMERIC_BOUNDS.items():
        bound = criteria.get(key)
        if bound is None:
            continue
        value = car.get(field)
        if not _is_number(value):
            return False  # valeur absente ou invalide : l'annonce ne peut pas prouver qu'elle respecte la borne
        strict = bool(criteria.get(f"{key}_strict"))
        if side == "max" and (value >= bound if strict else value > bound):
            return False
        if side == "min" and (value <= bound if strict else value < bound):
            return False
    return True


def filter_cars(cars: list[dict], criteria: dict) -> list[dict]:
    return [c for c in cars if matches(c, criteria or {})]


def sort_cars(cars: list[dict], option: str = DEFAULT_SORT) -> list[dict]:
    key, reverse = SORT_OPTIONS.get(option, SORT_OPTIONS[DEFAULT_SORT])
    valid = [c for c in cars if is_valid_record(c)]  # une annonce mal formée ne fait pas planter le tri
    return sorted(valid, key=key, reverse=reverse)


def search(cars: list[dict], criteria: dict, sort: str = DEFAULT_SORT) -> list[dict]:
    return sort_cars(filter_cars(cars, criteria), sort)


def dataset_stats(cars: list[dict]) -> dict:
    prices = [c["prix"] for c in cars] or [0]
    return {
        "total": len(cars),
        "brands": sorted({c["marque"] for c in cars}),
        "cities": sorted({c["ville"] for c in cars}),
        "fuels": dict(Counter(c["carburant"] for c in cars).most_common()),
        "categories": dict(Counter(c["categorie"] for c in cars).most_common()),
        "years": sorted({c["annee"] for c in cars}),
        "price_min": min(prices),
        "price_max": max(prices),
        "price_avg": round(sum(prices) / len(prices)),
    }


def _ceil(value: float, step: int) -> int:
    return int(-(-value // step) * step)


def _floor(value: float, step: int) -> int:
    return int(value // step * step)


# Message envoyé au chatbot pour retirer un critère (utilisé par les puces ✕ et les suggestions).
REMOVAL_MESSAGES = {
    "ville": "peu importe la ville",
    "carburant": "peu importe le carburant",
    "marque": "peu importe la marque",
    "modele": "peu importe le modèle",
    "categorie": "peu importe la catégorie",
    "boite": "peu importe la boîte",
    "prix_max": "sans limite de prix",
    "prix_min": "sans prix minimum",
    "kilometrage_max": "sans limite de kilométrage",
    "kilometrage_min": "sans kilométrage minimum",
    "annee_min": "peu importe l'année",
    "annee_max": "peu importe l'année",
}


def suggest_followups(cars: list[dict], criteria: dict, limit: int = 4) -> list[dict]:
    """Réponses rapides contextuelles pour AFFINER une recherche qui a des résultats.
    Chaque proposition est calculée sur les données (nombre réel de résultats),
    réduit la liste sans la vider, et n'est jamais appliquée automatiquement."""
    from .chatbot import format_int  # import local : évite un cycle

    current = filter_cars(cars, criteria)
    n = len(current)
    if n < 2:
        return []
    options: list[dict] = []

    def add(label: str, message: str, extra: dict) -> None:
        count = len(filter_cars(current, extra))
        if 0 < count < n:
            options.append({"label": label, "message": message, "count": count})

    if "ville" not in criteria:
        city = Counter(c["ville"] for c in current).most_common(1)[0][0]
        add(f"À {city}", f"à {city} seulement", {"ville": city})
    if "carburant" not in criteria:
        fuel = Counter(c["carburant"] for c in current).most_common(1)[0][0]
        add(f"{fuel} uniquement", f"{fuel.lower()} uniquement", {"carburant": fuel})
    if "prix_max" not in criteria:
        prices = sorted(c["prix"] for c in current)
        budget = max(5000, _floor(prices[len(prices) // 2], 5000))
        add(f"Moins de {format_int(budget)} DT", f"budget maximum {budget} DT", {"prix_max": budget})
    if "annee_min" not in criteria and "annee_max" not in criteria:
        years = sorted(c["annee"] for c in current)
        year = years[len(years) // 2]
        add(f"Depuis {year}", f"depuis {year}", {"annee_min": year})
    if "kilometrage_max" not in criteria:
        kms = sorted(c["kilometrage"] for c in current)
        km = max(10000, _floor(kms[len(kms) // 2], 10000))
        add(f"Moins de {format_int(km)} km", f"moins de {km} km",
            {"kilometrage_max": km, "kilometrage_max_strict": True})
    if "boite" not in criteria:
        add("Automatique", "boîte automatique", {"boite": "Automatique"})
    return options[:limit]


def highlight_badges(results: list[dict]) -> dict[str, list[str]]:
    """Repères visuels sur les résultats affichés (au moins 3 résultats)."""
    if len(results) < 3:
        return {}
    badges: dict[str, list[str]] = {}
    for label, best in (("Meilleur prix", min(results, key=lambda c: (c["prix"], c["kilometrage"]))),
                        ("Plus faible km", min(results, key=lambda c: (c["kilometrage"], c["prix"]))),
                        ("Plus récente", max(results, key=lambda c: (c["annee"], -c["prix"])))):
        badges.setdefault(best["id"], []).append(label)
    return badges


def suggest_relaxations(cars: list[dict], criteria: dict, limit: int = 4) -> list[dict]:
    """Propositions pour élargir une recherche vide, dans un ordre fixe (budget, kilométrage,
    carburant, zone…). Elles ne sont JAMAIS appliquées automatiquement : chacune fournit le
    message que l'utilisateur envoie d'un clic, et le nombre réel de résultats obtenus."""
    from .chatbot import format_km, format_price  # import local : évite un cycle

    options: list[dict] = []

    def add(label: str, message: str, new_criteria: dict) -> None:
        n = len(filter_cars(cars, new_criteria))
        if n:
            options.append({"label": label, "message": message, "count": n})

    if criteria.get("prix_max"):
        new = _ceil(criteria["prix_max"] * 1.25, 1000)
        add(f"Augmenter le budget à {format_price(new)}", f"augmente le budget à {new} DT",
            {**{k: v for k, v in criteria.items() if k != "prix_max_strict"}, "prix_max": new})
    if criteria.get("kilometrage_max"):
        new = _ceil(criteria["kilometrage_max"] * 1.3, 10000)
        add(f"Accepter jusqu'à {format_km(new)}", f"kilométrage maximum {new} km",
            {**{k: v for k, v in criteria.items() if k != "kilometrage_max_strict"}, "kilometrage_max": new})
    if criteria.get("prix_min"):
        add("Supprimer le prix minimum", REMOVAL_MESSAGES["prix_min"],
            {k: v for k, v in criteria.items() if not k.startswith("prix_min")})
    if criteria.get("kilometrage_min"):
        add("Supprimer le kilométrage minimum", REMOVAL_MESSAGES["kilometrage_min"],
            {k: v for k, v in criteria.items() if not k.startswith("kilometrage_min")})
    removable = {
        "carburant": "Supprimer le critère de carburant",
        "ville": "Étendre la zone de recherche",
        "boite": "Accepter toutes les boîtes",
        "modele": "Tous les modèles de la marque",
        "marque": "Toutes les marques",
        "categorie": "Toutes les catégories",
    }
    for key, label in removable.items():
        message = REMOVAL_MESSAGES[key]
        if criteria.get(key):
            reduced = {k: v for k, v in criteria.items() if k != key}
            if key == "marque":
                reduced.pop("modele", None)
            add(label, message, reduced)
    if criteria.get("annee_min") or criteria.get("annee_max"):
        add("Toutes les années", REMOVAL_MESSAGES["annee_min"],
            {k: v for k, v in criteria.items() if k not in ("annee_min", "annee_max")})
    return options[:limit]


def compare_to(car: dict, context: list[dict]) -> list[str]:
    """Résumé comparatif d'un véhicule face aux autres résultats de la même recherche."""
    from .chatbot import format_int  # import local : évite un cycle

    others = [c for c in context if c["id"] != car["id"]]
    if not others:
        return []
    lines = []
    for key, unit, label in (("prix", "DT", "Prix"), ("kilometrage", "km", "Kilométrage")):
        avg = sum(c[key] for c in others) / len(others)
        diff = round(100 * (car[key] - avg) / avg) if avg else 0
        if diff == 0:
            pos = "dans la moyenne"
        else:
            pos = f"{abs(diff)} % {'sous' if diff < 0 else 'au-dessus de'} la moyenne"
        lines.append(f"{label} {pos} des autres résultats ({format_int(round(avg))} {unit}).")
    older = sum(1 for c in others if c["annee"] < car["annee"])
    newer = sum(1 for c in others if c["annee"] > car["annee"])
    if newer == 0 and older == len(others):
        lines.append("C'est la plus récente des résultats.")
    elif newer == 0:
        lines.append("Parmi les plus récentes des résultats.")
    elif older == 0:
        lines.append("Parmi les plus anciennes des résultats.")
    else:
        lines.append(f"Plus récente que {older} des {len(others)} autres résultats.")
    return lines
