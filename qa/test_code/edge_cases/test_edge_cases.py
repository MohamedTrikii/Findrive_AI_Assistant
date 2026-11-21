"""EC — Cas limites et gestion d'erreurs : saisies invalides, valeurs extrêmes, jeux de données défectueux.

Règle vérifiée partout : l'application ne plante jamais et n'invente jamais de critère.
Les tests « jeu de données » copient les modules RÉELS de l'application dans un dossier temporaire avec
un cars.json volontairement défectueux, puis exécutent le vrai app.py (AppTest).
"""

import copy
import json
import shutil
import time

from conftest import CARS, ROOT, WELCOME, ask, displayed_cards, oracle, public, send, shot, show_exchange
from streamlit.testing.v1 import AppTest

from findrive.chatbot import Vocabulary, process_message
from findrive.search import filter_cars, sort_cars, suggest_followups, suggest_relaxations

PACKAGE = "findrive"


def app_with_dataset(tmp_path, content):
    """Copie l'application réelle ; content=None => pas de cars.json ; str => texte brut ; sinon JSON."""
    shutil.copy(ROOT / "app.py", tmp_path / "app.py")
    shutil.copytree(ROOT / PACKAGE, tmp_path / PACKAGE, ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "data").mkdir()
    if content is not None:
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        (tmp_path / "data" / "cars.json").write_text(text, encoding="utf-8")
    return AppTest.from_file(str(tmp_path / "app.py"), default_timeout=90)


def all_text(at):
    parts = [m.value for m in at.markdown] + [e.value for e in at.error] + [i.value for i in at.info]
    return " ".join(str(p) for p in parts)


def test_EC01_empty_message(page, evidence):
    turn, ids = ask("")
    blank, _ = ask("    ")
    before = page.locator('[data-testid="stChatMessage"]').count()
    box = page.get_by_test_id("stChatInputTextArea")
    box.fill("   ")
    box.press("Enter")
    time.sleep(1.5)
    after = page.locator('[data-testid="stChatMessage"]').count()
    path = shot(page, "edge_cases", "EC-01")
    evidence.update(engine_empty=(turn.intent, turn.criteria, turn.response), engine_blank=blank.criteria,
                    ui_messages_before=before, ui_messages_after=after,
                    welcome_still_visible=page.locator(WELCOME).count() == 1, screenshot=path)
    assert turn.criteria == {} and blank.criteria == {}
    assert after == before == 0          # message vide ignoré, rien n'est ajouté
    assert page.locator(WELCOME).count() == 1


def test_EC02_unknown_city(page, evidence):
    turn, ids = ask("voiture à Paris")
    turn2, _ = ask("voiture à Tozeur")
    turn3, _ = ask("Voiture à Atlantis")
    send(page, "voiture à Paris")
    show_exchange(page)
    path = shot(page, "edge_cases", "EC-02")
    evidence.turn(turn, ids)
    evidence.update(tozeur=(turn2.criteria, turn2.warnings), atlantis=(turn3.criteria, turn3.warnings),
                    ui_cards=len(displayed_cards(page)), screenshot=path)
    for t in (turn, turn2, turn3):
        assert "ville" not in t.criteria          # aucune ville inventée
        assert any("ville" in w.lower() or "disponible" in w.lower() for w in t.warnings)
    assert displayed_cards(page) == []            # pas de faux résultats


def test_EC03_price_zero(evidence):
    turn, ids = ask("voiture à 0 DT")
    turn2, _ = ask("moins de 0 DT", {"ville": "Tunis"})
    evidence.turn(turn, ids)
    evidence.update(with_context=(turn2.intent, turn2.criteria, turn2.warnings))
    assert "prix_max" not in turn.criteria and turn.warnings
    assert public(turn2.criteria) == {"ville": "Tunis"}   # contexte conservé, 0 DT refusé


def test_EC04_negative_price(page, evidence):
    msg = "Voiture moins de -5000 DT"
    turn, ids = ask(msg)
    send(page, msg)
    show_exchange(page)
    path = shot(page, "edge_cases", "EC-04")
    evidence.turn(turn, ids)
    evidence.update(screenshot=path)
    assert turn.criteria.get("prix_max") != 5000, "le signe « - » ne doit pas être ignoré (‑5000 ≠ 5000)"
    assert "prix_max" not in turn.criteria
    assert any("négati" in w for w in turn.warnings)


def test_EC05_extremely_large_mileage(evidence):
    turn, ids = ask("moins de 999999999999 km")
    turn2, ids2 = ask("moins de 10" + "0" * 40 + " DT")
    evidence.turn(turn, ids)
    evidence.update(huge_price=(turn2.criteria, len(ids2)))
    assert turn.criteria.get("kilometrage_max") == 999999999999
    assert ids == oracle()                                  # toutes les voitures, aucun plantage
    assert len(ids2) == 200


def test_EC06_misspelled_words(evidence):
    got = {m: public(ask(m)[0].criteria) for m in ("Peugot diesel", "renaut à sousse", "toyta hybride", "voiture a tunis")}
    evidence.update(extracted=got)
    assert got["Peugot diesel"] == {"marque": "Peugeot", "carburant": "Diesel"}
    assert got["renaut à sousse"] == {"marque": "Renault", "ville": "Sousse"}
    assert got["toyta hybride"] == {"marque": "Toyota", "carburant": "Hybride"}
    assert got["voiture a tunis"] == {"ville": "Tunis"}


def test_EC07_unknown_brand(evidence):
    turn, ids = ask("Je cherche une Tesla")
    turn2, _ = ask("Tesla", {"ville": "Tunis"})
    evidence.turn(turn, ids)
    evidence.update(with_context=(turn2.intent, turn2.criteria))
    assert "marque" not in turn.criteria
    assert any("Tesla" in w for w in turn.warnings)
    assert public(turn2.criteria) == {"ville": "Tunis"}


def test_EC08_unknown_fuel_type(page, evidence):
    msg = "voiture au GPL"
    turn, ids = ask(msg)
    send(page, msg)
    show_exchange(page)
    path = shot(page, "edge_cases", "EC-08")
    evidence.turn(turn, ids)
    evidence.update(screenshot=path)
    assert "carburant" not in turn.criteria
    assert any("GPL" in w for w in turn.warnings), "le carburant inconnu doit être signalé, pas ignoré en silence"


def test_EC09_contradictory_criteria(evidence):
    turn, ids = ask("voiture à plus de 50000 DT et moins de 30000 DT")
    turn2, ids2 = ask("diesel électrique")
    evidence.turn(turn, ids)
    evidence.update(multi_fuel=(turn2.criteria, len(ids2)))
    assert ids == []
    assert any("contradictoire" in w.lower() for w in turn.warnings)
    assert ids2 == sorted(oracle(carburant="Diesel") + oracle(carburant="Électrique"))  # interprété comme « ou »


def test_EC10_missing_dataset(tmp_path, evidence):
    at = app_with_dataset(tmp_path, None).run()
    text = all_text(at)
    at.chat_input(key="chat_msg").set_value("voiture à Tunis").run()
    evidence.update(exception=bool(at.exception), notice="introuvable" in text,
                    criteria=at.session_state.criteria, results=len(at.session_state.messages[-1].get("ids", [])))
    assert not at.exception
    assert "introuvable" in text
    assert len(at.session_state.messages[-1]["ids"]) == 46   # base de démonstration générée en mémoire


def test_EC11_malformed_records(tmp_path, evidence):
    cars = copy.deepcopy(CARS[:30])
    cars[0]["prix"] = None
    del cars[1]["modele"]
    cars[2]["kilometrage"] = "beaucoup"
    cars[3] = "pas un objet"
    del cars[4]["ville"]
    errors = {}
    for label, call in {
        "filter": lambda: filter_cars(cars, {"prix_max": 40000}),
        "sort": lambda: sort_cars([c for c in cars if isinstance(c, dict)]),
        "vocab": lambda: Vocabulary.from_cars(cars),
        "chat": lambda: process_message("Peugeot à Tunis moins de 40000 DT", {}, cars),
    }.items():
        try:
            call()
        except Exception as exc:  # noqa: BLE001
            errors[label] = f"{type(exc).__name__}: {exc}"
    at = app_with_dataset(tmp_path, {"metadata": {}, "cars": cars}).run()
    usable = not at.exception and any(ci.key == "chat_msg" for ci in at.chat_input)
    if usable:
        at.chat_input(key="chat_msg").set_value("moins de 40000 DT").run()
    evidence.update(engine_errors=errors, app_exception=[str(e.value)[:200] for e in at.exception],
                    app_usable=usable, app_errors=[x.value[:200] for x in at.error], app_text=all_text(at)[:300])
    assert errors == {}, errors
    assert not at.exception
    assert usable, "une seule annonce défectueuse ne doit pas rendre l'application inutilisable"
    assert "ignorée" in all_text(at)          # l'utilisateur est informé des annonces écartées


def test_EC12_empty_dataset(tmp_path, evidence):
    at = app_with_dataset(tmp_path, {"metadata": {"count": 0}, "cars": []}).run()
    exc0 = [str(e.value)[:200] for e in at.exception]
    if not at.exception:
        at.chat_input(key="chat_msg").set_value("diesel à Tunis").run()
    evidence.update(exception=exc0 or [str(e.value)[:200] for e in at.exception],
                    last=at.session_state.messages[-1]["text"] if not at.exception else None)
    assert not at.exception
    assert at.session_state.messages[-1]["ids"] == []
    assert suggest_relaxations([], {"ville": "Tunis"}) == [] and suggest_followups([], {}) == []


def test_EC13_corrupted_json(tmp_path, evidence):
    at = app_with_dataset(tmp_path, '{"cars": [ {"id": "A", ').run()
    errs = [e.value for e in at.error]
    evidence.update(error_messages=errs, exception=[str(e.value)[:200] for e in at.exception])
    assert not at.exception
    assert errs and "Impossible de lire cars.json" in errs[0]


def test_EC14_repeated_messages(evidence):
    t1, ids1 = ask("diesel à Tunis")
    t2, ids2 = ask("diesel à Tunis", t1.criteria)
    t3, ids3 = ask("diesel à Tunis", t2.criteria)
    evidence.update(criteria=[t1.criteria, t2.criteria, t3.criteria], counts=[len(ids1), len(ids2), len(ids3)],
                    response_3=t3.response)
    assert t1.criteria == t2.criteria == t3.criteria
    assert ids1 == ids2 == ids3
    assert "déjà actifs" in t3.response


def test_EC15_unexpected_language_and_long_input(evidence):
    en, en_ids = ask("I want a diesel car in Tunis")
    emoji, _ = ask("🚗🚗🔥")
    t0 = time.time()
    long_turn, _ = ask("voiture " * 2000)
    duration = time.time() - t0
    sql, _ = ask("'; DROP TABLE cars; -- <script>alert(1)</script>")
    evidence.update(english=(en.criteria, len(en_ids)), emoji=(emoji.intent, emoji.criteria),
                    long_input_seconds=round(duration, 3), injection=(sql.intent, sql.criteria))
    assert public(en.criteria) == {"carburant": "Diesel", "ville": "Tunis"}   # mots-clés reconnus, pas d'invention
    assert emoji.criteria == {} and sql.criteria == {}
    assert duration < 2
