"""FT — Tests fonctionnels (point de vue utilisateur) sur l'application RÉELLE et le jeu de données RÉEL.

Chaque test :
1. tape le message dans le vrai champ de conversation (Chrome piloté par Playwright) ;
2. déplie toutes les pages de résultats (« Afficher … de plus ») ;
3. vérifie chaque carte affichée contre l'enregistrement du jeu de données (via l'identifiant du conteneur) ;
4. compare l'ensemble complet des résultats du moteur à l'oracle indépendant ;
5. enregistre les critères réellement extraits et une capture d'écran réelle.
"""

import time

from conftest import (
    BY_ID,
    ask,
    chip_labels,
    displayed_cards,
    last_assistant,
    oracle,
    public,
    send,
    shot,
    show_exchange,
    wait_idle,
)


def expand_all(pg, max_clicks=12):
    for _ in range(max_clicks):
        more = last_assistant(pg).get_by_role("button", name="voitures de plus")
        if not more.count():
            more = last_assistant(pg).locator("button", has_text="de plus")
        if not more.count():
            return
        more.first.click()
        time.sleep(0.3)
        wait_idle(pg)


def run_scenario(pg, evidence, msg, expected_ids, check, *, shot_name, previous=None, expand=True):
    turn, ids = ask(msg, previous)
    send(pg, msg)
    show_exchange(pg)
    path = shot(pg, "functional", shot_name)
    if expand:
        expand_all(pg)
    cards = displayed_cards(pg)
    bad = [c["id"] for c in cards if not check(BY_ID[c["id"]])]
    text = last_assistant(pg).inner_text()
    evidence.turn(turn, ids)
    evidence.update(input=msg, expected_count=len(expected_ids), engine_count=len(ids),
                    displayed_count=len(cards), violating_cards=bad, chips=chip_labels(pg),
                    screenshot=path, ui_text=" ".join(text.split())[:400])
    return turn, ids, cards, bad, text


def test_FT01_search_without_precise_criteria(page, evidence):
    turn, ids, cards, bad, text = run_scenario(page, evidence, "Voiture", oracle(), lambda c: True,
                                               shot_name="FT-01", expand=False)
    assert public(turn.criteria) == {}                         # aucun filtre inutile
    assert ids == oracle() and len(ids) == 200                 # toutes les annonces valides
    assert "200" in turn.response and "filtre" in turn.response  # l'assistant explique ce qu'il a compris
    assert len(cards) == 6 and "Afficher" in text              # résultats directement dans le chat


def test_FT02_search_by_city(page, evidence):
    expected = oracle(ville="Tunis")
    turn, ids, cards, bad, _ = run_scenario(page, evidence, "Voiture à Tunis", expected,
                                            lambda c: c["ville"] == "Tunis", shot_name="FT-02")
    assert public(turn.criteria) == {"ville": "Tunis"}
    assert ids == expected
    assert len(cards) == len(expected) and not bad
    assert chip_labels(page) == ["Tunis"]


def test_FT03_search_by_max_price_and_fuel(page, evidence):
    expected = oracle(carburant="Diesel", prix_lt=40000)
    turn, ids, cards, bad, _ = run_scenario(page, evidence, "Voiture diesel moins de 40000 DT", expected,
                                            lambda c: c["carburant"] == "Diesel" and c["prix"] < 40000,
                                            shot_name="FT-03")
    if cards:
        worst = max(cards, key=lambda c: BY_ID[c["id"]]["prix"])
        target = page.locator(f'[class*="st-key-card_"][class*="{worst["id"]}"]').first
        evidence["max_displayed_price"] = BY_ID[worst["id"]]["prix"]
        evidence["screenshot_validation"] = shot(page, "functional", "FT-03_validation", target)
    assert turn.criteria.get("carburant") == "Diesel" and turn.criteria.get("prix_max") == 40000
    assert ids == expected
    assert not bad, f"cartes qui violent « diesel < 40 000 DT » : {bad}"


def test_FT04_multi_criteria(page, evidence):
    msg = "Je cherche une voiture diesel à Tunis moins de 40000 DT avec moins de 100000 km."
    expected = oracle(ville="Tunis", carburant="Diesel", prix_lt=40000, km_lt=100000)
    turn, ids, cards, bad, _ = run_scenario(
        page, evidence, msg, expected,
        lambda c: c["ville"] == "Tunis" and c["carburant"] == "Diesel" and c["prix"] < 40000
        and c["kilometrage"] < 100000, shot_name="FT-04_results")
    assert public(turn.criteria) == {"ville": "Tunis", "carburant": "Diesel", "prix_max": 40000,
                                     "kilometrage_max": 100000}
    assert ids == expected
    assert len(cards) == len(expected) and not bad


def test_FT05_ambiguous_request(page, evidence):
    msg = "Je veux une voiture très bien, quelque chose de bon."
    turn, ids, cards, bad, text = run_scenario(page, evidence, msg, oracle(), lambda c: True,
                                               shot_name="FT-05", expand=False)
    assert public(turn.criteria) == {}                          # aucun critère inventé
    assert turn.intent in ("no_criteria", "ambiguous")          # recherche large ou question
    assert chip_labels(page) == []
    assert page.get_by_test_id("stChatInputTextArea").is_enabled()  # l'interface reste utilisable
    send(page, "diesel")
    assert displayed_cards(page), "l'interface doit rester fonctionnelle après la demande ambiguë"


def test_FT06_search_by_brand(page, evidence):
    expected = oracle(marque="Peugeot")
    turn, ids, cards, bad, _ = run_scenario(page, evidence, "Je cherche une Peugeot", expected,
                                            lambda c: c["marque"] == "Peugeot", shot_name="FT-06")
    assert public(turn.criteria) == {"marque": "Peugeot"}
    assert ids == expected and not bad and len(cards) == len(expected)


def test_FT07_search_by_model(page, evidence):
    expected = oracle(marque="Renault", modele="Clio")
    turn, ids, cards, bad, _ = run_scenario(page, evidence, "Je cherche une Clio", expected,
                                            lambda c: c["modele"] == "Clio", shot_name="FT-07")
    assert public(turn.criteria) == {"marque": "Renault", "modele": "Clio"}
    assert ids == expected and not bad and len(cards) == len(expected)


def test_FT08_search_by_min_price(page, evidence):
    expected = oracle(prix_gt=100000)
    turn, ids, cards, bad, _ = run_scenario(page, evidence, "Une voiture à plus de 100000 DT", expected,
                                            lambda c: c["prix"] > 100000, shot_name="FT-08")
    assert turn.criteria.get("prix_min") == 100000
    assert ids == expected and not bad and len(cards) == len(expected)


def test_FT09_change_criterion_in_conversation(page, evidence):
    send(page, "Je cherche une voiture diesel à Tunis")
    expected = oracle(carburant="Diesel", ville="Sfax")
    turn, ids, cards, bad, text = run_scenario(
        page, evidence, "plutôt à Sfax", expected, lambda c: c["ville"] == "Sfax" and c["carburant"] == "Diesel",
        shot_name="FT-09", previous={"carburant": "Diesel", "ville": "Tunis"})
    assert public(turn.criteria) == {"carburant": "Diesel", "ville": "Sfax"}
    assert turn.changed == {"ville": ("Tunis", "Sfax")}
    assert "Tunis → Sfax" in text
    assert ids == expected and not bad


def test_FT10_remove_criterion(page, evidence):
    send(page, "Peugeot diesel à Tunis")
    previous = {"marque": "Peugeot", "carburant": "Diesel", "ville": "Tunis"}
    expected = oracle(marque="Peugeot", carburant="Diesel")
    turn, ids, cards, bad, _ = run_scenario(
        page, evidence, "peu importe la ville", expected,
        lambda c: c["marque"] == "Peugeot" and c["carburant"] == "Diesel", shot_name="FT-10", previous=previous)
    assert public(turn.criteria) == {"marque": "Peugeot", "carburant": "Diesel"}
    assert turn.removed == {"ville": "Tunis"}
    assert ids == expected and not bad and len(cards) == len(expected)


def test_FT11_no_matching_vehicle(page, evidence):
    msg = "Voiture électrique à Gabès moins de 30000 DT"
    expected = oracle(carburant="Électrique", ville="Gabès", prix_lt=30000)
    turn, ids, cards, bad, text = run_scenario(page, evidence, msg, expected, lambda c: False,
                                               shot_name="FT-11", expand=False)
    assert expected == [] and ids == []
    assert public(turn.criteria) == {"carburant": "Électrique", "ville": "Gabès", "prix_max": 30000}
    assert cards == []
    assert page.locator(".am-empty").count() == 1
    assert "Aucune voiture" in text


def test_FT12_brand_fuel_city_price(page, evidence):
    msg = "Je cherche une Peugeot diesel à Tunis moins de 40000 DT."
    expected = oracle(marque="Peugeot", carburant="Diesel", ville="Tunis", prix_lt=40000)
    turn, ids, cards, bad, _ = run_scenario(
        page, evidence, msg, expected,
        lambda c: c["marque"] == "Peugeot" and c["carburant"] == "Diesel" and c["ville"] == "Tunis"
        and c["prix"] < 40000, shot_name="FT-12")
    assert public(turn.criteria) == {"marque": "Peugeot", "carburant": "Diesel", "ville": "Tunis", "prix_max": 40000}
    assert ids == expected and not bad and len(cards) == len(expected)


def test_FT13_reset_conversation_criteria(page, evidence):
    send(page, "Peugeot diesel à Tunis")
    turn, ids, cards, bad, text = run_scenario(page, evidence, "Nouvelle recherche", oracle(), lambda c: True,
                                               shot_name="FT-13", expand=False,
                                               previous={"marque": "Peugeot", "carburant": "Diesel", "ville": "Tunis"})
    assert turn.intent == "reset" and turn.criteria == {}
    assert "effacé tous les critères" in text
    send(page, "à Sfax")
    assert chip_labels(page) == ["Sfax"], "après réinitialisation, l'ancien contexte ne doit pas revenir"
