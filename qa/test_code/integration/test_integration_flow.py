"""IT — Tests d'intégration : chat ↔ analyse ↔ moteur de recherche ↔ données ↔ interface.

Les tests AppTest exécutent le vrai script app.py (sans navigateur) ; IT-04 et IT-05 pilotent
l'application réelle dans Chrome via Playwright et vérifient les cartes réellement affichées.
"""

import json

from conftest import BY_ID, CARS, ROOT, VOCAB, ask, displayed_cards, last_assistant, oracle, public, send, shot, show_exchange
from streamlit.testing.v1 import AppTest

from automind.chatbot import Vocabulary, parse_message, process_message
from automind.search import dataset_stats, filter_cars, load_dataset, search, sort_cars, suggest_followups, suggest_relaxations

APP = str(ROOT / "app.py")


def app_send(at, text):
    at.chat_input(key="chat_msg").set_value(text).run()
    assert not at.exception, at.exception
    return at


def test_IT01_chat_to_criteria_extraction(evidence):
    at = AppTest.from_file(APP, default_timeout=60).run()
    msg = "Je cherche une Peugeot diesel à Tunis"
    app_send(at, msg)
    extracted = parse_message(msg, VOCAB).criteria
    evidence.update(input=msg, session_criteria=at.session_state.criteria, parser_criteria=extracted,
                    messages=[m["role"] for m in at.session_state.messages])
    assert at.session_state.criteria == extracted
    assert public(extracted) == {"marque": "Peugeot", "carburant": "Diesel", "ville": "Tunis"}
    assert [m["role"] for m in at.session_state.messages] == ["user", "assistant"]


def test_IT02_criteria_to_search_engine(evidence):
    cases = {
        "voiture à Sfax": oracle(ville="Sfax"),
        "Peugeot essence": oracle(marque="Peugeot", carburant="Essence"),
        "diesel à Tunis moins de 40000 DT": oracle(ville="Tunis", carburant="Diesel", prix_lt=40000),
        "Renault à Ariana maximum 45000 DT": oracle(marque="Renault", ville="Ariana", prix_le=45000),
    }
    got = {}
    for msg, expected in cases.items():
        turn, ids = ask(msg)
        got[msg] = {"criteria": turn.criteria, "count": turn.result_count, "expected": len(expected)}
        assert ids == expected, msg
        assert turn.result_count == len(expected), msg
    evidence.update(cases=got)


def test_IT03_search_engine_and_dataset(evidence, tmp_path):
    cars, meta = load_dataset(ROOT / "data" / "cars.json")
    stats = dataset_stats(cars)
    vocab = Vocabulary.from_cars(cars)
    list_file = tmp_path / "liste.json"
    list_file.write_text(json.dumps(cars[:5], ensure_ascii=False), encoding="utf-8")
    as_list, meta_list = load_dataset(list_file)
    evidence.update(total=stats["total"], cities=len(vocab.cities), brands=len(set(vocab.brands.values())),
                    unique_ids=len({c["id"] for c in cars}), metadata=meta, list_format=len(as_list))
    assert len(cars) == meta["count"] == 200
    assert len({c["id"] for c in cars}) == 200
    assert len(vocab.cities) == 10 and len(set(vocab.brands.values())) == len(stats["brands"])
    assert len(as_list) == 5 and meta_list == {}
    assert len(search(cars, {})) == 200


def test_IT04_search_results_to_ui_cards(page, evidence):
    msg = "Peugeot à Tunis"
    send(page, msg)
    turn, _ = ask(msg)
    expected = [c["id"] for c in sort_cars(filter_cars(CARS, turn.criteria), "Prix croissant")]
    cards = displayed_cards(page)
    show_exchange(page)
    path = shot(page, "integration", "IT-04")
    mismatches = []
    for c in cards:
        car = BY_ID[c["id"]]
        if c["name"] != f'{car["marque"]} {car["modele"]}' or car["ville"] not in c["meta"] \
                or f'{car["prix"]:,}'.replace(",", " ") not in c["price_text"].replace(" ", " "):
            mismatches.append(c)
    evidence.update(input=msg, backend_ids=expected, displayed_ids=[c["id"] for c in cards],
                    displayed=[f'{c["name"]} | {c["meta"]} | {c["price_text"]}' for c in cards],
                    mismatches=mismatches, screenshot=path)
    assert [c["id"] for c in cards] == expected[:6]
    assert not mismatches


def test_IT05_multi_criteria_end_to_end(page, evidence):
    msg = "Je cherche une voiture diesel à Tunis moins de 40000 DT avec moins de 100000 km."
    send(page, msg)
    expected = oracle(ville="Tunis", carburant="Diesel", prix_lt=40000, km_lt=100000)
    cards = displayed_cards(page)
    text = last_assistant(page).inner_text()
    show_exchange(page)
    path = shot(page, "integration", "IT-05")
    violations = [c["id"] for c in cards if not (BY_ID[c["id"]]["ville"] == "Tunis" and
                                                 BY_ID[c["id"]]["carburant"] == "Diesel" and
                                                 BY_ID[c["id"]]["prix"] < 40000 and
                                                 BY_ID[c["id"]]["kilometrage"] < 100000)]
    evidence.update(input=msg, expected_ids=expected, displayed_ids=[c["id"] for c in cards],
                    displayed=[f'{c["name"]} | {c["meta"]} | {c["price_text"]} | {c["specs"]}' for c in cards],
                    violations=violations, response=text.split("\n")[2] if text.count("\n") > 2 else text,
                    screenshot=path)
    assert set(c["id"] for c in cards) <= set(expected)
    assert len(cards) == min(6, len(expected))
    assert not violations
    assert f"J'ai trouvé {len(expected)} " in text


def test_IT06_context_kept_between_messages(evidence):
    at = AppTest.from_file(APP, default_timeout=60).run()
    steps = []
    for msg in ("Je cherche une voiture diesel", "À Tunis seulement", "Maximum 40 000 DT", "plutôt à Sfax"):
        app_send(at, msg)
        steps.append((msg, public(dict(at.session_state.criteria)), at.session_state.messages[-1]["intent"]))
    evidence.update(steps=steps)
    assert steps[-1][1] == {"carburant": "Diesel", "ville": "Sfax", "prix_max": 40000}
    assert [s[2] for s in steps] == ["search", "follow_up", "follow_up", "follow_up"]
    last_ids = at.session_state.messages[-1]["ids"]
    assert sorted(last_ids) == oracle(carburant="Diesel", ville="Sfax", prix_le=40000)


def test_IT07_suggestions_match_real_search(evidence):
    """Le nombre affiché sur chaque bouton de suggestion = nombre réel obtenu en cliquant."""
    checked = []
    for start in ({"carburant": "Diesel"}, {"ville": "Tunis", "carburant": "Diesel", "prix_max": 25000}):
        for sug in suggest_followups(CARS, start) + suggest_relaxations(CARS, start):
            turn = process_message(sug["message"], start, CARS, VOCAB)
            checked.append((sug["label"], sug["count"], turn.result_count))
    evidence.update(checked=checked)
    assert checked
    assert all(announced == real for _, announced, real in checked), checked


def test_IT08_manual_filters_to_chat(evidence):
    at = AppTest.from_file(APP, default_timeout=60).run()
    app_send(at, "Peugeot à Tunis")
    synced = at.selectbox(key="mf_ville").value
    at.selectbox(key="mf_ville").set_value("Sfax")
    next(b for b in at.button if b.label == "Appliquer dans la conversation").click().run()
    evidence.update(widget_synced_to=synced, criteria_after=at.session_state.criteria,
                    last_user=at.session_state.messages[-2]["text"])
    assert not at.exception
    assert synced == "Tunis"
    assert public(at.session_state.criteria) == {"marque": "Peugeot", "ville": "Sfax"}
    assert sorted(at.session_state.messages[-1]["ids"]) == oracle(marque="Peugeot", ville="Sfax")
