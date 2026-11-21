"""Tests fonctionnels et tests du chatbot — exécutés sur test_fixtures.json
(12 véhicules fixes) pour des résultats déterministes.

Lancer : python -m pytest -v
"""

import json
from pathlib import Path

import pytest

from findrive.chatbot import Vocabulary, describe_criteria, parse_message, process_message
from findrive.search import (
    REMOVAL_MESSAGES,
    SORT_OPTIONS,
    filter_cars,
    highlight_badges,
    search,
    sort_cars,
    suggest_followups,
    suggest_relaxations,
)

FIXTURES = json.loads((Path(__file__).resolve().parent.parent / "data" / "test_fixtures.json").read_text(encoding="utf-8"))["cars"]
VOCAB = Vocabulary.from_cars(FIXTURES)


def run(message, previous=None):
    turn = process_message(message, previous or {}, FIXTURES, VOCAB)
    ids = sorted(c["id"] for c in filter_cars(FIXTURES, turn.criteria))
    return turn, ids


# ---------------------------------------------------------------------------
# Les 5 scénarios fonctionnels obligatoires (T01 à T05 dans test_plan.csv)
# ---------------------------------------------------------------------------

def test_T01_recherche_par_ville(record_property):
    turn, ids = run("voiture à Tunis")
    record_property("observed", f"criteria={turn.criteria} ids={ids}")
    assert turn.intent == "search"
    assert turn.criteria == {"ville": "Tunis"}
    assert ids == ["FIX-001", "FIX-002", "FIX-005", "FIX-006", "FIX-007", "FIX-008"]


def test_T02_carburant_et_prix_maximum(record_property):
    turn, ids = run("diesel moins de 40000 DT")
    record_property("observed", f"criteria={turn.criteria} ids={ids}")
    assert turn.criteria == {"carburant": "Diesel", "prix_max": 40000, "prix_max_strict": True}
    # FIX-003 (59 000 DT) et FIX-011 (48 000 DT) sont exclus ; FIX-008 (40 000 DT pile) aussi :
    # « moins de » est une borne STRICTE (exigence FT-03 de la campagne de tests).
    assert ids == ["FIX-001", "FIX-002"]
    # Une borne « maximum » reste inclusive : FIX-008 revient.
    assert run("diesel maximum 40000 DT")[1] == ["FIX-001", "FIX-002", "FIX-008"]


def test_T03_prix_maximum_seul(record_property):
    turn, ids = run("moins de 40 000 DT")
    record_property("observed", f"criteria={turn.criteria} ids={ids}")
    assert turn.criteria == {"prix_max": 40000, "prix_max_strict": True}
    assert ids == ["FIX-001", "FIX-002", "FIX-004", "FIX-005"]
    assert all(c["prix"] < 40000 for c in filter_cars(FIXTURES, turn.criteria))


def test_T04_criteres_combines(record_property):
    turn, ids = run("diesel à Tunis moins de 40000 DT et moins de 100000 km")
    record_property("observed", f"criteria={turn.criteria} ids={ids}")
    assert turn.criteria == {"ville": "Tunis", "carburant": "Diesel", "prix_max": 40000, "prix_max_strict": True,
                             "kilometrage_max": 100000, "kilometrage_max_strict": True}
    assert turn.recognized_count == 4
    assert ids == ["FIX-001", "FIX-002"]  # FIX-008 (40 000 DT et 100 000 km pile) exclu : bornes strictes


def test_T05_aucun_resultat(record_property):
    turn, ids = run("diesel à Sousse moins de 30000 DT")
    record_property("observed", f"criteria={turn.criteria} ids={ids} response={turn.response!r}")
    assert turn.criteria == {"ville": "Sousse", "carburant": "Diesel", "prix_max": 30000, "prix_max_strict": True}
    assert ids == []
    assert turn.result_count == 0
    assert "Je n'ai trouvé aucune voiture correspondant exactement à ces critères" in turn.response


# ---------------------------------------------------------------------------
# Compréhension du langage (expressions de l'énoncé)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,strict", [("moins de 40 000 DT", True), ("inférieure à 40 000", True),
                                         ("sous 40 000 DT", True), ("maximum 40 000", False),
                                         ("budget de 40 000", False), ("ne dépasse pas 40 000", False),
                                         ("jusqu'à 40 000 dinars", False), ("budget max 40k", False),
                                         ("pas plus de 40 000 DT", False)])
def test_expressions_prix(text, strict):
    expected = {"prix_max": 40000, "prix_max_strict": True} if strict else {"prix_max": 40000}
    assert parse_message(text, VOCAB).criteria == expected


@pytest.mark.parametrize("text,strict", [("moins de 100 000 km", True), ("maximum 100000 km", False),
                                         ("ne dépasse pas 100 000 kilomètres", False), ("moins de 100k km", True)])
def test_expressions_kilometrage(text, strict):
    expected = {"kilometrage_max": 100000, "kilometrage_max_strict": True} if strict else {"kilometrage_max": 100000}
    assert parse_message(text, VOCAB).criteria == expected


@pytest.mark.parametrize("text,expected", [
    ("plus de 30 000 DT", {"prix_min": 30000, "prix_min_strict": True}),
    ("au moins 30 000 DT", {"prix_min": 30000}),
    ("à partir de 30 000 DT", {"prix_min": 30000}),
    ("entre 30 000 et 40 000 DT", {"prix_min": 30000, "prix_max": 40000}),
])
def test_expressions_prix_minimum(text, expected):
    assert parse_message(text, VOCAB).criteria == expected


@pytest.mark.parametrize("text,city", [("à Tunis", "Tunis"), ("sur Tunis", "Tunis"), ("de Tunis", "Tunis"),
                                       ("à Sfax", "Sfax"), ("à Sousse", "Sousse"), ("à Monastir", "Monastir"),
                                       ("à Bizerte", "Bizerte"), ("à Ariana", "Ariana")])
def test_expressions_ville(text, city):
    assert parse_message(text, VOCAB).criteria == {"ville": city}


@pytest.mark.parametrize("text,fuel", [("diesel", "Diesel"), ("gasoil", "Diesel"), ("gazole", "Diesel"),
                                       ("essence", "Essence"), ("voiture électrique", "Électrique"),
                                       ("hybride", "Hybride")])
def test_expressions_carburant(text, fuel):
    assert parse_message(text, VOCAB).criteria["carburant"] == fuel


@pytest.mark.parametrize("text,expected", [
    ("de 2020", {"annee_min": 2020, "annee_max": 2020}),
    ("année 2021", {"annee_min": 2021, "annee_max": 2021}),
    ("modèle 2019", {"annee_min": 2019, "annee_max": 2019}),
    ("après 2018", {"annee_min": 2019}),
    ("depuis 2020", {"annee_min": 2020}),
    ("avant 2022", {"annee_max": 2021}),
    ("entre 2018 et 2021", {"annee_min": 2018, "annee_max": 2021}),
])
def test_expressions_annee(text, expected):
    assert parse_message(text, VOCAB).criteria == expected


def test_marque_et_modele_issus_des_donnees():
    assert parse_message("une Peugeot 208", VOCAB).criteria == {"marque": "Peugeot", "modele": "208"}
    assert parse_message("Golf", VOCAB).criteria == {"marque": "Volkswagen", "modele": "Golf"}
    assert parse_message("citroen c3", VOCAB).criteria == {"marque": "Citroën", "modele": "C3"}


def test_modele_2008_n_est_pas_une_annee():
    assert parse_message("Peugeot 2008", VOCAB).criteria == {"marque": "Peugeot", "modele": "2008"}
    assert parse_message("Peugeot de 2019", VOCAB).criteria == {"marque": "Peugeot", "annee_min": 2019,
                                                                "annee_max": 2019}


def test_modele_inconnu_non_invente():
    r = parse_message("Peugeot 3008", VOCAB)
    assert r.criteria == {"marque": "Peugeot"}
    assert any("3008" in w for w in r.warnings)


def test_toyota_apres_2020():
    turn, ids = run("Toyota après 2020")
    assert turn.criteria == {"marque": "Toyota", "annee_min": 2021}
    assert ids == ["FIX-009"]


# ---------------------------------------------------------------------------
# Conversation multi-tours, réinitialisation, ambiguïtés
# ---------------------------------------------------------------------------

def test_suivi_ajoute_ville_au_carburant():
    t1, _ = run("Je cherche une voiture diesel.")
    t2, ids = run("À Tunis seulement.", t1.criteria)
    assert t2.intent == "follow_up"
    assert t2.criteria == {"carburant": "Diesel", "ville": "Tunis"}
    assert t2.added == {"ville": "Tunis"}
    assert "j'ajoute Ville = Tunis" in t2.response
    assert ids == ["FIX-001", "FIX-002", "FIX-008"]


def test_suivi_ajoute_prix_a_la_marque():
    t1, _ = run("Je cherche une Peugeot.")
    t2, ids = run("Maximum 40 000 DT.", t1.criteria)
    assert t2.intent == "follow_up"
    assert t2.criteria == {"marque": "Peugeot", "prix_max": 40000}
    assert ids == ["FIX-001", "FIX-002"]


def test_suivi_modifie_et_retire():
    t1, _ = run("diesel à Tunis")
    t2, _ = run("plutôt à Sfax", t1.criteria)
    assert t2.changed == {"ville": ("Tunis", "Sfax")}
    t3, _ = run("peu importe la ville", t2.criteria)
    assert t3.criteria == {"carburant": "Diesel"}
    assert t3.removed == {"ville": "Sfax"}


@pytest.mark.parametrize("text", ["Nouvelle recherche", "Réinitialiser", "Oublie les critères précédents",
                                  "Recommencer"])
def test_reinitialisation(text):
    previous = {"carburant": "Diesel", "ville": "Tunis", "prix_max": 40000}
    turn, ids = run(text, previous)
    assert turn.intent == "reset"
    assert turn.criteria == {}
    assert len(ids) == len(FIXTURES)


def test_reinitialisation_avec_nouveaux_criteres():
    turn, _ = run("Nouvelle recherche : Kia à Tunis", {"carburant": "Diesel"})
    assert turn.criteria == {"marque": "Kia", "ville": "Tunis"}


def test_terme_vague_devient_un_tri_sans_inventer_de_budget():
    # « pas chère » n'invente aucun montant : les critères sont gardés, l'ordre devient « prix croissant »
    # et l'assistant invite à préciser un budget.
    previous = {"marque": "Peugeot"}
    turn, _ = run("une voiture pas chère", previous)
    assert turn.intent == "sort"
    assert turn.sort == "Prix croissant"
    assert turn.criteria == previous
    assert "prix_max" not in turn.criteria
    assert "40 000 DT" in turn.response


def test_demande_imprecise_reste_ambigue():
    previous = {"ville": "Sfax", "prix_max": 40000}
    turn, _ = run("augmente le budget", previous)
    assert turn.intent == "ambiguous"
    assert turn.criteria == previous
    assert any("nouveau budget" in w for w in turn.warnings)


def test_aucun_critere_affiche_tout():
    turn, ids = run("Je cherche une voiture")
    assert turn.intent == "no_criteria"
    assert turn.criteria == {}
    assert len(ids) == len(FIXTURES)


def test_demande_hors_perimetre():
    turn, _ = run("je veux louer une voiture", {"ville": "Tunis"})
    assert turn.intent == "unsupported"
    assert turn.criteria == {"ville": "Tunis"}


def test_ville_inconnue_signalee_et_non_appliquee():
    turn, _ = run("Peugeot à Paris")
    assert turn.criteria == {"marque": "Peugeot"}
    assert any("Paris" in w for w in turn.warnings)


def test_montant_trop_faible_non_applique():
    r = parse_message("moins de 40 DT", VOCAB)
    assert "prix_max" not in r.criteria
    assert r.warnings


def test_structure_resultat():
    d = process_message("diesel à Tunis moins de 40 000 DT et 100 000 km", {}, FIXTURES, VOCAB).to_dict()
    assert d["intent"] == "search"
    assert d["criteria"] == {"ville": "Tunis", "carburant": "Diesel", "prix_max": 40000, "prix_max_strict": True,
                             "kilometrage_max": 100000}
    assert d["warnings"] == []
    assert d["recognized_count"] == 4


# ---------------------------------------------------------------------------
# Tri et suggestions : ne modifient jamais l'ensemble des résultats
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("option", list(SORT_OPTIONS))
def test_tri_ne_change_pas_les_resultats(option):
    criteria = {"ville": "Tunis"}
    base = filter_cars(FIXTURES, criteria)
    sorted_ = search(FIXTURES, criteria, option)
    assert sorted(c["id"] for c in sorted_) == sorted(c["id"] for c in base)


def test_tri_prix_croissant():
    prices = [c["prix"] for c in sort_cars(FIXTURES, "Prix croissant")]
    assert prices == sorted(prices)


def test_suggestions_non_appliquees():
    criteria = {"ville": "Tunis", "carburant": "Diesel", "prix_max": 35000}
    suggestions = suggest_relaxations(FIXTURES, criteria)
    assert criteria == {"ville": "Tunis", "carburant": "Diesel", "prix_max": 35000}  # inchangés
    assert suggestions[0] == {"label": "Augmenter le budget à 44 000 DT",
                              "message": "augmente le budget à 44000 DT", "count": 3}
    # Le message proposé, une fois envoyé, est bien compris comme une modification du budget.
    turn, ids = run(suggestions[0]["message"], criteria)
    assert "je passe le budget de 35 000 DT à 44 000 DT" in turn.response
    assert turn.changed == {"prix_max": (35000, 44000)}
    assert ids == ["FIX-001", "FIX-002", "FIX-008"]
    # Aucune suggestion n'est inventée quand aucun assouplissement simple ne suffit.
    assert suggest_relaxations(FIXTURES, {"ville": "Sousse", "carburant": "Diesel", "prix_max": 30000}) == []


def test_description_criteres():
    assert describe_criteria({"annee_min": 2021}) == [("Année minimum", "2021")]
    assert describe_criteria({"annee_min": 2020, "annee_max": 2020}) == [("Année", "2020")]


# ---------------------------------------------------------------------------
# Expérience conversationnelle : réponses rapides, puces ✕, repères
# ---------------------------------------------------------------------------

def test_reponses_rapides_affinent_sans_vider(record_property):
    criteria = {"ville": "Tunis"}
    before = dict(criteria)
    n = len(filter_cars(FIXTURES, criteria))
    followups = suggest_followups(FIXTURES, criteria)
    record_property("observed", " | ".join(f"{s['label']} → {s['count']}" for s in followups).replace(" ", " "))
    assert criteria == before  # jamais appliquées automatiquement
    assert followups
    for sug in followups:
        assert 0 < sug["count"] < n
        # Le message proposé est bien compris par le chatbot comme un suivi
        turn, ids = run(sug["message"], criteria)
        assert turn.intent == "follow_up", sug
        assert turn.criteria["ville"] == "Tunis"
        assert len(ids) == sug["count"], sug


def test_reponses_rapides_ne_reproposent_pas_un_critere_actif():
    followups = suggest_followups(FIXTURES, {"ville": "Tunis", "carburant": "Diesel"})
    assert all("Tunis" not in s["label"] and "Diesel" not in s["label"] for s in followups)


def test_pas_de_reponse_rapide_sans_resultat():
    assert suggest_followups(FIXTURES, {"ville": "Sousse", "carburant": "Diesel"}) == []


@pytest.mark.parametrize("key", ["ville", "carburant", "marque", "modele", "categorie", "boite",
                                 "prix_max", "kilometrage_max", "annee_min"])
def test_puce_retrait_retire_exactement_le_critere(key):
    full = {"marque": "Peugeot", "modele": "208", "ville": "Tunis", "carburant": "Diesel", "categorie": "Citadine",
            "boite": "Manuelle", "prix_max": 40000, "kilometrage_max": 100000, "annee_min": 2018, "annee_max": 2020}
    turn, _ = run(REMOVAL_MESSAGES[key], full)
    assert turn.intent == "follow_up"
    expected_removed = {"annee_min", "annee_max"} if key == "annee_min" else {key}
    if key == "marque":
        expected_removed.add("modele")
    assert set(turn.removed) == expected_removed
    assert set(turn.criteria) == set(full) - expected_removed


def test_reperes_meilleur_prix_km_annee():
    results = filter_cars(FIXTURES, {"ville": "Tunis"})
    badges = highlight_badges(results)
    assert badges["FIX-005"] == ["Meilleur prix"]          # 37 000 DT
    assert "Plus faible km" in badges["FIX-006"]           # 44 000 km
    assert "Plus récente" in badges["FIX-006"] or "Plus récente" in badges["FIX-007"]
    assert highlight_badges(results[:2]) == {}             # pas de repère sous 3 résultats


# ---------------------------------------------------------------------------
# Interface conversationnelle : contexte, valeurs multiples, tri, retraits
# ---------------------------------------------------------------------------

def test_conversation_de_reference_de_la_consigne(record_property):
    """Diesel → budget → « plus récents » : les critères sont conservés à chaque étape."""
    t1, ids1 = run("Je cherche une voiture diesel à Tunis.")
    t2, ids2 = run("Budget maximum 40 000 dinars.", t1.criteria)
    t3, ids3 = run("Montre-moi des modèles plus récents.", t2.criteria)
    record_property("observed", f"{t1.criteria} → {t2.criteria} → sort={t3.sort} | {t2.response}")
    assert t1.criteria == {"ville": "Tunis", "carburant": "Diesel"}
    assert t2.intent == "follow_up"
    assert t2.criteria == {"ville": "Tunis", "carburant": "Diesel", "prix_max": 40000}
    assert t2.response.startswith("D'accord, je limite la recherche à 40 000 DT.")
    assert t3.intent == "sort"
    assert t3.sort == "Année la plus récente"
    assert t3.criteria == t2.criteria
    assert ids3 == ids2 == ["FIX-001", "FIX-002", "FIX-008"]
    assert "plus récents" in t3.response


def test_contexte_conserve_par_defaut():
    t1, _ = run("Je cherche une voiture diesel")
    t2, _ = run("Je cherche une Peugeot", t1.criteria)
    assert t2.intent == "follow_up"
    assert t2.criteria == {"carburant": "Diesel", "marque": "Peugeot"}


def test_nouvelle_recherche_explicite_repart_de_zero():
    turn, _ = run("Nouvelle recherche : Kia", {"carburant": "Diesel", "ville": "Tunis"})
    assert turn.intent == "search"
    assert turn.criteria == {"marque": "Kia"}
    assert turn.replaced_previous


def test_plusieurs_marques(record_property):
    turn, ids = run("Je cherche une Peugeot ou une Renault à moins de 40 000 dinars.")
    record_property("observed", f"criteria={turn.criteria} ids={ids}")
    assert turn.criteria == {"marque": ["Peugeot", "Renault"], "prix_max": 40000, "prix_max_strict": True}
    assert turn.warnings == []
    assert ids == ["FIX-001", "FIX-002"]  # FIX-008 (Renault à 40 000 DT pile) exclu : « moins de » est strict
    assert "Peugeot ou Renault" in turn.response


def test_plusieurs_villes_et_carburants():
    turn, ids = run("diesel ou hybride à Tunis ou Sousse")
    assert turn.criteria == {"ville": ["Tunis", "Sousse"], "carburant": ["Diesel", "Hybride"]}
    assert ids == ["FIX-001", "FIX-002", "FIX-008", "FIX-009"]


def test_enleve_une_valeur_d_un_critere_multiple():
    turn, ids = run("Enlève Renault", {"marque": ["Peugeot", "Renault"], "prix_max": 40000})
    assert turn.criteria == {"marque": "Peugeot", "prix_max": 40000}
    assert ids == ["FIX-001", "FIX-002"]


def test_enleve_le_critere_diesel():
    turn, _ = run("Enlève le critère diesel.", {"carburant": "Diesel", "ville": "Tunis"})
    assert turn.intent == "follow_up"
    assert turn.criteria == {"ville": "Tunis"}
    assert turn.removed == {"carburant": "Diesel"}


def test_enlever_un_critere_absent_est_signale():
    turn, _ = run("Enlève le critère diesel", {"ville": "Tunis"})
    assert turn.criteria == {"ville": "Tunis"}
    assert "n'était pas un critère actif" in turn.response


def test_augmente_le_budget():
    turn, ids = run("Augmente le budget à 50 000 DT.", {"ville": "Tunis", "prix_max": 40000})
    assert turn.changed == {"prix_max": (40000, 50000)}
    assert ids == ["FIX-001", "FIX-002", "FIX-005", "FIX-006", "FIX-007", "FIX-008"]


@pytest.mark.parametrize("text,expected", [
    ("Montre-moi des modèles plus récents", "Année la plus récente"),
    ("Montre-moi des voitures récentes", "Année la plus récente"),
    ("Je veux quelque chose de moins cher", "Prix croissant"),
    ("Je cherche une voiture économique", "Prix croissant"),
    ("les moins kilométrées d'abord", "Kilométrage croissant"),
    ("privilégie le prix", "Prix croissant"),
    ("privilégie le kilométrage", "Kilométrage croissant"),
    ("privilégie l'année", "Année la plus récente"),
    ("les plus chères", "Prix décroissant"),
])
def test_preferences_d_ordre(text, expected):
    previous = {"ville": "Tunis"}
    turn, _ = run(text, previous)
    assert turn.intent == "sort"
    assert turn.sort == expected
    assert turn.criteria == previous  # un tri ne modifie jamais les critères


def test_tri_demande_avec_un_critere():
    turn, _ = run("une voiture récente à Tunis")
    assert turn.criteria == {"ville": "Tunis"}
    assert turn.sort == "Année la plus récente"


def test_demande_complete_de_la_consigne():
    turn, _ = run("Je cherche une voiture automatique à Sfax, moins de 50 000 DT, avec moins de 100 000 km.")
    assert turn.criteria == {"ville": "Sfax", "boite": "Automatique", "prix_max": 50000, "prix_max_strict": True,
                             "kilometrage_max": 100000, "kilometrage_max_strict": True}


def test_description_naturelle():
    from findrive.chatbot import natural_description
    assert natural_description({"carburant": "Diesel", "ville": "Sfax", "prix_max": 40000}, 6) == \
        "voitures diesel à Sfax jusqu'à 40 000 DT"
    assert natural_description({"boite": "Automatique", "categorie": "SUV"}, 2) == "SUV automatiques"
    assert natural_description({"marque": ["Peugeot", "Renault"]}, 1) == "voiture Peugeot ou Renault"


def test_comparaison_dans_la_fiche():
    from findrive.search import compare_to
    context = filter_cars(FIXTURES, {"ville": "Tunis"})
    car = next(c for c in FIXTURES if c["id"] == "FIX-005")  # 37 000 DT, le moins cher de Tunis
    lines = compare_to(car, context)
    assert len(lines) == 3
    assert "sous la moyenne" in lines[0]
    assert compare_to(car, [car]) == []
