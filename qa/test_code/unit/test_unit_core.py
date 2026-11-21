"""UT — Tests unitaires : extraction des critères, normalisation, filtres, tri, validation des données."""

import copy

from conftest import CARS, VOCAB, public

from automind.chatbot import normalize, parse_message
from automind.search import SORT_OPTIONS, filter_cars, matches, sort_cars
from automind.validation import validate_cars


def extract(message):
    return parse_message(message, VOCAB)


def car(**kw):
    base = {"id": "T", "marque": "Peugeot", "modele": "208", "annee": 2019, "ville": "Tunis",
            "carburant": "Diesel", "prix": 40000, "kilometrage": 100000, "boite": "Manuelle",
            "categorie": "Citadine", "etat": "Bon", "source": "test"}
    base.update(kw)
    return base


def test_UT01_extract_city(evidence):
    r = extract("Je cherche une voiture à Tunis")
    evidence.update(input="Je cherche une voiture à Tunis", extracted=r.criteria)
    assert public(r.criteria) == {"ville": "Tunis"}


def test_UT02_extract_fuel_and_synonyms(evidence):
    got = {m: extract(m).criteria.get("carburant") for m in
           ("Je veux une voiture diesel", "voiture gasoil", "une voiture au gazole", "voiture essence",
            "voiture électrique", "voiture hybride")}
    evidence.update(extracted=got)
    assert got == {"Je veux une voiture diesel": "Diesel", "voiture gasoil": "Diesel",
                   "une voiture au gazole": "Diesel", "voiture essence": "Essence",
                   "voiture électrique": "Électrique", "voiture hybride": "Hybride"}


def test_UT03_extract_max_price_strict(evidence):
    r = extract("moins de 40000 DT")
    at_limit = filter_cars([car(prix=40000), car(id="U", prix=39999)], r.criteria)
    evidence.update(input="moins de 40000 DT", extracted=r.criteria,
                    car_at_40000_kept=any(c["id"] == "T" for c in at_limit))
    assert r.criteria.get("prix_max") == 40000
    assert [c["id"] for c in at_limit] == ["U"], "« moins de 40000 » doit exclure une voiture à 40 000 DT"


def test_UT04_extract_max_mileage(evidence):
    r = extract("moins de 100000 km")
    kept = [c["id"] for c in filter_cars([car(kilometrage=100000), car(id="U", kilometrage=99999)], r.criteria)]
    evidence.update(input="moins de 100000 km", extracted=r.criteria, kept=kept)
    assert r.criteria.get("kilometrage_max") == 100000
    assert "prix_max" not in r.criteria
    assert kept == ["U"]


def test_UT05_extract_brand(evidence):
    got = {m: extract(m).criteria.get("marque") for m in ("Je cherche une Peugeot", "une vw", "Citroen", "mercedes-benz")}
    evidence.update(extracted=got)
    assert got == {"Je cherche une Peugeot": "Peugeot", "une vw": "Volkswagen", "Citroen": "Citroën",
                   "mercedes-benz": "Mercedes"}


def test_UT06_extract_model_not_year(evidence):
    clio = extract("Je cherche une Clio").criteria
    p2008 = extract("Peugeot 2008").criteria
    y2008 = extract("une voiture de 2018").criteria
    evidence.update(clio=clio, peugeot_2008=p2008, annee_2018=y2008)
    assert public(clio) == {"marque": "Renault", "modele": "Clio"}
    assert public(p2008) == {"marque": "Peugeot", "modele": "2008"}       # modèle, pas une année
    assert y2008 == {"annee_min": 2018, "annee_max": 2018}               # année, pas un modèle


def test_UT07_extract_min_price(evidence):
    r = extract("plus de 30000 DT")
    evidence.update(input="plus de 30000 DT", extracted=r.criteria, warnings=r.warnings)
    assert r.criteria.get("prix_min") == 30000
    assert "prix_max" not in r.criteria


def test_UT08_numeric_formats(evidence):
    forms = ["moins de 40000 DT", "moins de 40 000 DT", "moins de 40k DT", "moins de 40.000 DT",
             "moins de 40 000 dinars", "budget max 40k"]
    got = {f: extract(f).criteria.get("prix_max") for f in forms}
    evidence.update(extracted=got)
    assert set(got.values()) == {40000}


def test_UT09_normalization_case_accents(evidence):
    got = {m: extract(m).criteria.get("ville") for m in ("voiture à GABÈS", "voiture a gabes", "Voiture à Gabès")}
    evidence.update(extracted=got, normalized=normalize("Électrique À GABÈS"))
    assert set(got.values()) == {"Gabès"}
    assert normalize("Électrique À GABÈS") == "electrique a gabes"
    assert len(normalize("Série 3 – Peugeot’s")) == len("Série 3 – Peugeot’s")  # positions conservées


def test_UT10_inclusive_maximum_phrasings(evidence):
    forms = ["maximum 40000 DT", "jusqu'à 40000 DT", "au plus 40000 DT", "pas plus de 40000 DT",
             "budget 40000 DT", "prix inférieur ou égal à 40000 DT"]
    got, kept = {}, {}
    for f in forms:
        crit = extract(f).criteria
        got[f] = crit.get("prix_max")
        kept[f] = bool(filter_cars([car(prix=40000)], crit)) if crit.get("prix_max") else None
    evidence.update(extracted=got, car_at_40000_kept=kept)
    assert all(v == 40000 for v in got.values()), got
    assert all(kept.values()), "une borne « maximum » doit inclure 40 000 DT"


def test_UT11_filter_function_boundaries(evidence):
    cars = [car(id="A", prix=39999), car(id="B", prix=40000), car(id="C", prix=40001, ville="Sfax")]
    res = {
        "le_40000": [c["id"] for c in cars if matches(c, {"prix_max": 40000})],
        "tunis": [c["id"] for c in cars if matches(c, {"ville": "tunis"})],
        "liste_villes": [c["id"] for c in cars if matches(c, {"ville": ["Sfax", "Tunis"]})],
        "vide": [c["id"] for c in filter_cars(cars, {})],
        "none": [c["id"] for c in filter_cars(cars, None)],
    }
    evidence.update(results=res)
    assert res == {"le_40000": ["A", "B"], "tunis": ["A", "B"], "liste_villes": ["A", "B", "C"],
                   "vide": ["A", "B", "C"], "none": ["A", "B", "C"]}


def test_UT12_sorting_logic(evidence):
    out = {}
    for option in SORT_OPTIONS:
        s = sort_cars(CARS, option)
        out[option] = [s[0]["id"], s[-1]["id"]]
        key = {"Prix croissant": ("prix", False), "Prix décroissant": ("prix", True),
               "Kilométrage croissant": ("kilometrage", False), "Année la plus récente": ("annee", True)}[option]
        values = [c[key[0]] for c in s]
        assert values == sorted(values, reverse=key[1]), option
    assert len(sort_cars(CARS, "option inconnue")) == len(CARS)  # option inconnue -> tri par défaut
    evidence.update(first_last=out)


def test_UT13_dataset_validation(evidence):
    errors_real = validate_cars(CARS)
    broken = copy.deepcopy(CARS[:20])
    broken[0]["prix"] = -10
    broken[1].pop("ville")
    broken[2]["id"] = broken[3]["id"]
    errors_broken = validate_cars(broken)
    evidence.update(real_dataset_errors=errors_real, corrupted_errors=errors_broken[:5])
    assert errors_real == []
    assert len(errors_broken) >= 3


def test_UT14_unknown_criteria_not_invented(evidence):
    r = extract("une voiture rouge avec GPS")
    evidence.update(input="une voiture rouge avec GPS", extracted=r.criteria, warnings=r.warnings)
    assert r.criteria == {}
    assert len(r.warnings) == 2  # couleur + GPS signalés, jamais transformés en filtre
