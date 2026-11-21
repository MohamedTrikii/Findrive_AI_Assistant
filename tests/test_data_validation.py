"""Tests du jeu de données : génération reproductible, validation, plausibilité,
et scénarios de démonstration sur cars.json."""

import json
from pathlib import Path

import pytest

from automind.catalog import PREMIUM_BRANDS
from automind.chatbot import Vocabulary, process_message
from automind.generate_cars import build_document, generate_dataset, load_fixtures
from automind.search import filter_cars, load_dataset
from automind.validation import summarize, validate_cars

HERE = Path(__file__).resolve().parent.parent
DEMO_PROMPTS = [
    "voiture à Tunis",
    "diesel moins de 40000 DT",
    "Peugeot à Sfax",
    "essence à Tunis moins de 45000 DT",
    "diesel à Tunis moins de 40000 DT et moins de 100000 km",
    "Toyota après 2020",
    "SUV de moins de 60 000 DT",
    "Peugeot essence à Sfax",
]


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset(200, 42)


def test_taille_minimale(dataset):
    assert len(dataset) == 200
    assert len(generate_dataset(100, 1)) == 100


def test_generation_reproductible(dataset):
    assert generate_dataset(200, 42) == dataset
    assert generate_dataset(200, 7) != dataset


def test_fichier_cars_json_correspond_a_la_graine_par_defaut(dataset):
    on_disk = json.loads((HERE / "data" / "cars.json").read_text(encoding="utf-8"))
    assert on_disk == json.loads(json.dumps(build_document(dataset, 42), ensure_ascii=False))


def test_validation_reussie(dataset):
    assert validate_cars(dataset) == []


def test_validation_cars_json():
    cars, meta = load_dataset(HERE / "data" / "cars.json")
    assert meta["synthetic"] is True
    assert validate_cars(cars) == []


def test_validation_fixtures():
    assert validate_cars(load_fixtures()) == []


def test_fixtures_incluses_dans_la_base(dataset):
    ids = {c["id"] for c in dataset}
    assert {c["id"] for c in load_fixtures()} <= ids


def _first_valid(dataset):
    return dict(dataset[20])


@pytest.mark.parametrize("mutation,expected", [
    (lambda c: c.update(prix=-5), "prix invalide"),
    (lambda c: c.update(kilometrage=0), "kilométrage invalide"),
    (lambda c: c.update(marque="Tesla"), "marque inconnue"),
    (lambda c: c.update(marque="Renault", modele="Golf"), "invalide pour Renault"),
    (lambda c: c.update(ville="Paris"), "ville inconnue"),
    (lambda c: c.update(carburant="GPL"), "carburant inconnu"),
    (lambda c: c.update(annee=1990), "année invalide"),
    (lambda c: c.pop("ville"), "champs manquants"),
])
def test_validation_detecte_les_erreurs(dataset, mutation, expected):
    car = _first_valid(dataset)
    mutation(car)
    errors = validate_cars([car])
    assert any(expected in e for e in errors), errors


def test_validation_detecte_doublons(dataset):
    car = _first_valid(dataset)
    twin = dict(car)
    errors = validate_cars([car, twin])
    assert any("Identifiant dupliqué" in e for e in errors)
    twin["id"] = "AM-9999"
    assert any("Annonce dupliquée" in e for e in validate_cars([car, twin]))


def test_variete(dataset):
    s = summarize(dataset)
    assert s["brand_count"] >= 15
    assert s["city_count"] == 10
    assert set(s["fuels"]) == {"Essence", "Diesel", "Hybride", "Électrique"}
    assert set(s["categories"]) == {"Citadine", "Compacte", "Berline", "SUV"}


def test_plausibilite(dataset):
    s = summarize(dataset)
    assert s["premium_avg_price"] > 1.5 * s["generalist_avg_price"]
    assert s["old_avg_km"] > 2 * s["recent_avg_km"]
    for car in dataset:
        if car["carburant"] == "Électrique":
            assert car["boite"] == "Automatique" and car["annee"] >= 2018
    assert all(car["marque"] in PREMIUM_BRANDS or car["prix"] < 200000 for car in dataset)


@pytest.mark.parametrize("prompt", DEMO_PROMPTS)
def test_prompts_de_demonstration_donnent_des_resultats(prompt):
    cars, _ = load_dataset(HERE / "data" / "cars.json")
    turn = process_message(prompt, {}, cars, Vocabulary.from_cars(cars))
    assert turn.intent == "search" and turn.warnings == []
    matches = filter_cars(cars, turn.criteria)
    assert len(matches) >= 1
    assert turn.result_count == len(matches)
