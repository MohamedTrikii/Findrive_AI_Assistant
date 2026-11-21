"""RT — Suite de régression : scénarios déjà validés, rejoués après chaque correction.

RT-01 à RT-05 : rejoués dans l'application réelle (navigateur) + contrôle du moteur sur cars.json.
RT-06 : la suite de tests d'origine du projet (test_chatbot.py, test_data_validation.py, test_app.py).
RT-07 : le tableau « Démonstration » du README correspond toujours aux résultats réels.
RT-08 : le scénario conversationnel conseillé du README fonctionne toujours étape par étape.
"""

import re
import subprocess
import sys

from conftest import BY_ID, ROOT, ask, chip_labels, displayed_cards, oracle, public, send, shot, show_exchange


def ui_check(page, msg, category_name, check):
    send(page, msg)
    cards = displayed_cards(page)
    show_exchange(page)
    path = shot(page, "regression", category_name)
    return cards, [c["id"] for c in cards if not check(BY_ID[c["id"]])], path


def test_RT01_basic_search(page, evidence):
    turn, ids = ask("Je cherche une voiture")
    cards, bad, path = ui_check(page, "Je cherche une voiture", "RT-01", lambda c: True)
    evidence.turn(turn, ids)
    evidence.update(ui_cards=len(cards), screenshot=path)
    assert public(turn.criteria) == {} and len(ids) == 200 and len(cards) == 6


def test_RT02_city_filter(page, evidence):
    turn, ids = ask("voiture à Sousse")
    cards, bad, path = ui_check(page, "voiture à Sousse", "RT-02", lambda c: c["ville"] == "Sousse")
    evidence.turn(turn, ids)
    evidence.update(ui_cards=len(cards), violations=bad, screenshot=path)
    assert ids == oracle(ville="Sousse") and not bad


def test_RT03_price_filter(page, evidence):
    strict, s_ids = ask("moins de 30000 DT")
    incl, i_ids = ask("maximum 30000 DT")
    cards, bad, path = ui_check(page, "moins de 30000 DT", "RT-03", lambda c: c["prix"] < 30000)
    evidence.turn(strict, s_ids)
    evidence.update(strict_count=len(s_ids), inclusive_count=len(i_ids), violations=bad, screenshot=path,
                    at_30000=[i for i in i_ids if BY_ID[i]["prix"] == 30000])
    assert s_ids == oracle(prix_lt=30000)
    assert i_ids == oracle(prix_le=30000)
    assert not bad


def test_RT04_multi_criteria(page, evidence):
    msg = "essence à Tunis moins de 45000 DT"
    turn, ids = ask(msg)
    cards, bad, path = ui_check(page, msg, "RT-04", lambda c: c["ville"] == "Tunis" and c["carburant"] == "Essence"
                                and c["prix"] < 45000)
    evidence.turn(turn, ids)
    evidence.update(ui_cards=len(cards), violations=bad, screenshot=path)
    assert ids == oracle(ville="Tunis", carburant="Essence", prix_lt=45000) and not bad


def test_RT05_context_update(page, evidence):
    send(page, "Je cherche une voiture diesel")
    send(page, "à Tunis seulement")
    turn, ids = ask("maximum 40 000 DT", {"carburant": "Diesel", "ville": "Tunis"})
    cards, bad, path = ui_check(page, "maximum 40 000 DT", "RT-05",
                                lambda c: c["carburant"] == "Diesel" and c["ville"] == "Tunis" and c["prix"] <= 40000)
    chips = chip_labels(page)
    evidence.turn(turn, ids)
    evidence.update(chips=chips, violations=bad, screenshot=path)
    assert public(turn.criteria) == {"carburant": "Diesel", "ville": "Tunis", "prix_max": 40000}
    assert ids == oracle(carburant="Diesel", ville="Tunis", prix_le=40000) and not bad
    assert sorted(chips) == sorted(["Tunis", "Diesel", "Budget ≤ 40 000 DT"])  # « maximum » : borne inclusive


def test_RT06_original_project_suite(evidence):
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_chatbot.py",
                           "tests/test_data_validation.py", "tests/test_app.py"], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)
    summary = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-300:]
    failed = re.findall(r"^FAILED (\S+)", proc.stdout, re.M)
    evidence.update(summary=summary, failed=failed)
    assert proc.returncode == 0, summary


def test_RT07_readme_demo_table_still_true(evidence):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([^`]+)` \| [^|]+ \| (\d+) \|$", readme, re.M)
    got = []
    for msg, documented in rows:
        _, ids = ask(msg)
        got.append((msg, int(documented), len(ids)))
    evidence.update(rows=got)
    assert len(rows) == 6
    assert all(doc == real for _, doc, real in got), got


def test_RT08_readme_conversation_scenario(evidence):
    """Chaque message du scénario du README est rejoué dans l'ordre ; les nombres documentés doivent être exacts."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = readme.split("Scénario multi-tours")[1].split("##")[0]
    steps = re.findall(r"^\d\. `([^`]+)`(.*)$", block, re.M)
    ctx, log = {}, []
    for msg, rest in steps:
        if msg.startswith("Voir les détails"):  # clic sur une carte, pas un message : couvert par UI-08
            continue
        documented = re.search(r"→\s*(\d+)(?:\s*voitures?)?(?:\s*résultats?)?(?:,|\s*$)", rest)
        turn, ids = ask(msg, ctx)
        ctx = turn.criteria
        log.append((msg, turn.intent, public(ctx), len(ids), int(documented.group(1)) if documented else None))
    evidence.update(steps=log)
    assert len(log) >= 5
    assert all(doc is None or doc == real for *_, real, doc in log), log
    assert log[-1][1] == "reset" and log[-1][2] == {}
