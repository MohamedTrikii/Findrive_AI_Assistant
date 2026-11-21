"""Tests des deux risques identifiés (voir project_report.md §10).

R1 — Mauvaise interprétation d'un critère (négation, approximation).
R2 — Erreur de filtrage (bornes strictes/inclusives, annonces invalides, contexte multi-tours).

Les tests marqués xfail(strict=True) DÉMONTRENT un risque encore présent : ils échouent
aujourd'hui (affichés « xfail »). Quand le correctif sera fait, ils passeront et pytest
signalera « XPASS(strict) » : il suffira alors de retirer le marqueur.

Lancer : py -m pytest test_risques.py -v
"""

import json
from pathlib import Path

import pytest

from automind.chatbot import Vocabulary, describe_criteria, parse_message, process_message
from automind.search import clean_records, filter_cars, search

FIXTURES = json.loads((Path(__file__).resolve().parent.parent / "data" / "test_fixtures.json").read_text(encoding="utf-8"))["cars"]
VOCAB = Vocabulary.from_cars(FIXTURES)


def parse(message):
    return parse_message(message, VOCAB)


def run(message, previous=None):
    turn = process_message(message, previous or {}, FIXTURES, VOCAB)
    return turn, filter_cars(FIXTURES, turn.criteria)


# =====================================================================
# R1 — Mauvaise interprétation d'un critère
# =====================================================================

NEGATIONS = ["voiture pas diesel", "tout sauf diesel", "hors diesel", "à part le diesel"]


@pytest.mark.xfail(strict=True, reason="R1 : la négation n'est pas gérée (« pas diesel » -> Diesel)")
@pytest.mark.parametrize("message", NEGATIONS)
def test_r1_negation_ne_doit_pas_selectionner_la_valeur(message):
    r = parse(message)
    # Acceptable : critère ignoré avec avertissement, ou exclusion. Inacceptable : Carburant = Diesel.
    assert r.criteria.get("carburant") != "Diesel"


@pytest.mark.xfail(strict=True, reason="R1 : la négation passe sans avertissement")
def test_r1_negation_produit_un_avertissement():
    assert parse("voiture pas diesel").warnings


@pytest.mark.xfail(strict=True, reason="R1 : « autour de » est lu comme un prix maximum")
@pytest.mark.parametrize("message", ["autour de 40000 DT", "environ 40000 DT"])
def test_r1_approximation_donne_un_intervalle_ou_un_avertissement(message):
    r = parse(message)
    intervalle = "prix_min" in r.criteria and "prix_max" in r.criteria
    assert intervalle or r.warnings


@pytest.mark.parametrize("message, attendu", [
    ("diesel", {"carburant": "Diesel"}),
    ("moins de 40000 DT", {"prix_max": 40000, "prix_max_strict": True}),
    ("maximum 40000 DT", {"prix_max": 40000}),
    ("après 2020", {"annee_min": 2021}),
    ("avant 2018", {"annee_max": 2017}),
])
def test_r1_formulations_de_reference_bien_comprises(message, attendu):
    """Garde-fou : les formulations qui marchent aujourd'hui ne doivent pas régresser."""
    criteria = parse(message).criteria
    for key, value in attendu.items():
        assert criteria.get(key) == value
    if "prix_max" in attendu and "prix_max_strict" not in attendu:
        assert not criteria.get("prix_max_strict")


def test_r1_criteres_compris_sont_affiches_a_l_utilisateur():
    """Mesure de réduction : chaque critère compris est reformulé (puces), y compris le sens de la borne."""
    turn, _ = run("diesel moins de 40000 DT")
    labels = dict(describe_criteria(turn.criteria))
    assert labels["Carburant"] == "Diesel"
    assert labels["Prix maximum"].startswith("< ")


# =====================================================================
# R2 — Erreur de filtrage
# =====================================================================

def oracle(cars, champ, borne, sens, strict):
    """Comptage indépendant de search.matches() : on ne valide pas le code par lui-même."""
    if sens == "max":
        return {c["id"] for c in cars if (c[champ] < borne if strict else c[champ] <= borne)}
    return {c["id"] for c in cars if (c[champ] > borne if strict else c[champ] >= borne)}


@pytest.mark.parametrize("champ, cle", [("prix", "prix"), ("kilometrage", "kilometrage"), ("annee", "annee")])
@pytest.mark.parametrize("sens", ["max", "min"])
@pytest.mark.parametrize("strict", [False, True])
def test_r2_bornes_exactes_sur_valeurs_limites(champ, cle, sens, strict):
    """La borne est prise ÉGALE à une valeur réelle des fixtures : c'est le cas limite."""
    for borne in sorted({c[champ] for c in FIXTURES}):
        criteria = {f"{cle}_{sens}": borne}
        if strict:
            criteria[f"{cle}_{sens}_strict"] = True
        obtenu = {c["id"] for c in filter_cars(FIXTURES, criteria)}
        assert obtenu == oracle(FIXTURES, champ, borne, sens, strict), (criteria, borne)


def test_r2_strict_exclut_la_valeur_egale_inclusif_la_garde():
    prix = FIXTURES[0]["prix"]
    ident = FIXTURES[0]["id"]
    assert ident in {c["id"] for c in filter_cars(FIXTURES, {"prix_max": prix})}
    assert ident not in {c["id"] for c in filter_cars(FIXTURES, {"prix_max": prix, "prix_max_strict": True})}


@pytest.mark.parametrize("ajout", [
    {"carburant": "Diesel"}, {"ville": "Tunis"}, {"prix_max": 40000}, {"kilometrage_max": 100000},
    {"annee_min": 2019}, {"boite": "Automatique"},
])
@pytest.mark.parametrize("base", [{}, {"carburant": "Essence"}, {"prix_max": 60000}])
def test_r2_ajouter_un_critere_ne_fait_jamais_augmenter_les_resultats(base, ajout):
    if set(base) & set(ajout):
        pytest.skip("même clé : ce serait un remplacement, pas un ajout")
    avant = {c["id"] for c in filter_cars(FIXTURES, base)}
    apres = {c["id"] for c in filter_cars(FIXTURES, {**base, **ajout})}
    assert apres <= avant


def test_r2_annonces_invalides_sont_comptees_et_ne_font_pas_planter():
    abimees = FIXTURES[:3] + [
        {**FIXTURES[0], "id": "X1", "prix": None},
        {**FIXTURES[0], "id": "X2", "kilometrage": "beaucoup"},
        {k: v for k, v in FIXTURES[0].items() if k != "ville"} | {"id": "X3"},
        "pas un objet",
    ]
    valides, ecartees = clean_records(abimees)
    assert ecartees == 4  # l'écart doit être mesurable pour pouvoir être affiché
    assert {c["id"] for c in valides} == {c["id"] for c in FIXTURES[:3]}
    # Un filtre sur le prix écarte l'annonce sans prix…
    assert "X1" not in {c["id"] for c in filter_cars(abimees, {"prix_max": 10**9})}
    # …et la recherche complète (filtre + tri) n'affiche aucune annonce invalide.
    assert {c["id"] for c in search(abimees, {"prix_max": 10**9})} == {c["id"] for c in FIXTURES[:3]}


def test_r2_borne_stricte_conservee_au_tour_suivant():
    turn1, _ = run("moins de 40000 DT")
    turn2, resultats = run("diesel", turn1.criteria)
    assert turn2.criteria.get("prix_max") == 40000
    assert turn2.criteria.get("prix_max_strict") is True
    assert all(c["prix"] < 40000 and c["carburant"] == "Diesel" for c in resultats)


def test_r2_critere_herite_visible_puis_retirable():
    turn1, _ = run("voiture à Tunis")
    turn2, _ = run("diesel", turn1.criteria)
    assert "Ville" in dict(describe_criteria(turn2.criteria))  # le critère hérité est affiché
    turn3, _ = run("peu importe la ville", turn2.criteria)
    assert "ville" not in turn3.criteria and turn3.criteria.get("carburant") == "Diesel"


def test_r2_nouvelle_recherche_vide_le_contexte():
    turn1, _ = run("diesel à Tunis moins de 40000 DT")
    turn2, _ = run("nouvelle recherche", turn1.criteria)
    assert not turn2.criteria
