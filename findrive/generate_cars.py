"""Génération reproductible d'annonces automobiles FICTIVES pour Findrive Assistant.

Exemples :
    python -m findrive.generate_cars                    # 200 annonces, graine 42
    python -m findrive.generate_cars --count 300 --seed 7 --output cars_300.json

Les annonces de test de `test_fixtures.json` sont injectées en tête du fichier
(elles comptent dans --count) afin que les scénarios de démonstration donnent
toujours des résultats. Le reste est tiré aléatoirement avec une graine fixe.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from . import CARS_PATH, FIXTURES_PATH, SUMMARY_PATH
from .catalog import (
    BRANDS,
    CITIES,
    DIESEL,
    ELECTRIQUE,
    ESSENCE,
    HYBRIDE,
    MAX_YEAR,
    MIN_YEAR,
    REFERENCE_YEAR,
    models_of,
)
from .validation import _signature, summary_markdown, validate_cars

FUEL_WEIGHTS = {ESSENCE: 0.50, DIESEL: 0.35, HYBRIDE: 0.10, ELECTRIQUE: 0.05}
ANNUAL_KM = {DIESEL: (19000, 4000), ESSENCE: (12000, 3000), HYBRIDE: (13000, 3000), ELECTRIQUE: (9000, 2500)}
FUEL_PRICE_FACTOR = {ESSENCE: 1.00, DIESEL: 1.04, HYBRIDE: 1.10, ELECTRIQUE: 1.20}
CONDITION_FACTOR = {"Excellent": 1.05, "Très bon": 1.00, "Bon": 0.95, "Correct": 0.88}
CONDITION_ORDER = ["Excellent", "Très bon", "Bon", "Correct"]
YEARLY_RETENTION = 0.92  # décote fictive de 8 % par an


def load_fixtures(path: Path = FIXTURES_PATH) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [{k: v for k, v in car.items() if k != "role"} for car in data["cars"]]


def _round(value: float, step: int) -> int:
    return int(round(value / step) * step)


def _condition(rng: random.Random, age: int, km: int) -> str:
    if km < 40000 and age <= 3:
        level = 0
    elif km < 90000:
        level = 1
    elif km < 160000:
        level = 2
    else:
        level = 3
    if level < 3 and rng.random() < 0.15:  # quelques annonces moins bien entretenues
        level += 1
    return CONDITION_ORDER[level]


def generate_car(rng: random.Random, index: int) -> dict:
    brands = list(BRANDS)
    brand = rng.choices(brands, weights=[BRANDS[b][0] for b in brands])[0]
    premium = BRANDS[brand][1]
    model = rng.choice(list(models_of(brand)))
    category, new_price, fuels = models_of(brand)[model]
    fuel = rng.choices(fuels, weights=[FUEL_WEIGHTS[f] for f in fuels])[0]

    min_year = {ELECTRIQUE: 2018, HYBRIDE: 2016}.get(fuel, MIN_YEAR)
    year = max(min_year, min(MAX_YEAR, round(rng.gauss(2019, 3.5))))
    age = REFERENCE_YEAR - year

    mean_km, sd_km = ANNUAL_KM[fuel]
    annual = max(4000, rng.gauss(mean_km, sd_km))
    km = max(1500, _round(age * annual * rng.uniform(0.85, 1.15), 500))

    if fuel in (ELECTRIQUE, HYBRIDE):
        auto_p = 1.0 if fuel == ELECTRIQUE else 0.9
    elif premium:
        auto_p = 0.7
    elif category == "SUV":
        auto_p = 0.5
    else:
        auto_p = 0.2
    transmission = "Automatique" if rng.random() < auto_p else "Manuelle"
    condition = _condition(rng, age, km)

    # Prix fictif : prix neuf x décote x écart au kilométrage attendu x options x état x bruit
    expected_km = age * 14000
    km_factor = min(1.08, max(0.85, 1 - 0.25 * (km - expected_km) / 200000))
    fuel_factor = FUEL_PRICE_FACTOR[fuel] if len(fuels) > 1 else 1.0
    price = (
        new_price
        * YEARLY_RETENTION ** age
        * km_factor
        * fuel_factor
        * (1.04 if transmission == "Automatique" else 1.0)
        * CONDITION_FACTOR[condition]
        * rng.gauss(1.0, 0.05)
    )
    return {
        "id": f"AM-{index:04d}",
        "marque": brand,
        "modele": model,
        "annee": year,
        "ville": rng.choices(list(CITIES), weights=list(CITIES.values()))[0],
        "carburant": fuel,
        "prix": max(12000, _round(price, 500)),
        "kilometrage": km,
        "boite": transmission,
        "categorie": category,
        "etat": condition,
        "source": "synthetique",
    }


def generate_dataset(count: int = 200, seed: int = 42, include_fixtures: bool = True) -> list[dict]:
    rng = random.Random(seed)
    cars = load_fixtures() if include_fixtures else []
    if count < len(cars):
        raise ValueError(f"--count doit être ≥ {len(cars)} (nombre d'annonces de test)")
    seen = {_signature(c) for c in cars}
    index = 1
    while len(cars) < count:
        car = generate_car(rng, index)
        sig = _signature(car)
        if sig in seen:  # très rare : on retire une autre annonce
            continue
        seen.add(sig)
        cars.append(car)
        index += 1
    return cars


def build_document(cars: list[dict], seed: int) -> dict:
    return {
        "metadata": {
            "name": "Findrive Assistant — annonces synthétiques",
            "synthetic": True,
            "disclaimer": "Données fictives générées automatiquement. Les prix ne sont pas des valeurs du marché.",
            "seed": seed,
            "count": len(cars),
            "reference_year": REFERENCE_YEAR,
            "generator": "generate_cars.py v1.0",
        },
        "cars": cars,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Génère un jeu d'annonces automobiles fictives.")
    parser.add_argument("--count", type=int, default=200, help="nombre total d'annonces (défaut : 200)")
    parser.add_argument("--seed", type=int, default=42, help="graine aléatoire (défaut : 42)")
    parser.add_argument("--output", default=str(CARS_PATH), help="fichier JSON de sortie")
    parser.add_argument("--summary", default=str(SUMMARY_PATH), help="résumé Markdown ('' pour ne pas l'écrire)")
    args = parser.parse_args(argv)

    cars = generate_dataset(args.count, args.seed)
    errors = validate_cars(cars)
    doc = build_document(cars, args.seed)
    Path(args.output).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.summary:
        Path(args.summary).write_text(summary_markdown(cars, doc["metadata"], errors) + "\n", encoding="utf-8")

    print(f"{len(cars)} annonces écrites dans {args.output} (graine {args.seed})")
    if errors:
        print(f"ÉCHEC de la validation : {len(errors)} erreur(s)", file=sys.stderr)
        for e in errors[:20]:
            print("  -", e, file=sys.stderr)
        return 1
    print("Validation réussie.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
