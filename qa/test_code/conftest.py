"""Infrastructure commune de la campagne de tests AutoMind AI.

- Ajoute la racine du projet au sys.path (les modules testés sont ceux de l'application réelle).
- Fournit le jeu de données RÉEL (cars.json) et un ORACLE indépendant : les résultats attendus
  sont recalculés ici, sans utiliser search.matches(), pour ne pas valider le code par lui-même.
- Enregistre le « résultat réellement obtenu » de chaque test dans qa/results/actual_<phase>.json
  (phase = variable d'environnement TEST_PHASE, « final » par défaut). Le rapport est généré à partir de
  ces enregistrements : aucune valeur « obtenue » n'est écrite à la main.
- Démarre un serveur Streamlit dédié (port 8611) et fournit une page Playwright (Chrome/Edge installé).
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TESTING = ROOT / "qa"
SCREENSHOTS = TESTING / "screenshots"
RESULTS = TESTING / "results"
sys.path.insert(0, str(ROOT))

PHASE = os.environ.get("TEST_PHASE", "final")
PORT = int(os.environ.get("AUTOMIND_TEST_PORT", "8611"))
BASE_URL = f"http://localhost:{PORT}"
WELCOME = ".am-hero, .am-welcome"  # écran d'accueil (nouvelle et ancienne mise en page)

from automind.chatbot import Vocabulary, process_message  # noqa: E402
from automind.search import filter_cars, load_dataset  # noqa: E402

CARS, META = load_dataset(ROOT / "data" / "cars.json")
VOCAB = Vocabulary.from_cars(CARS)
BY_ID = {c["id"]: c for c in CARS}

# ------------------------------------------------------------------ oracle indépendant


def _fold(s) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", str(s).casefold()) if not unicodedata.combining(ch))


def oracle(cars=None, *, ville=None, carburant=None, marque=None, modele=None, prix_lt=None, prix_le=None,
           prix_gt=None, prix_ge=None, km_lt=None, km_le=None) -> list[str]:
    """Identifiants attendus, calculés directement sur les enregistrements."""
    out = []
    for c in CARS if cars is None else cars:
        if ville and _fold(c["ville"]) != _fold(ville):
            continue
        if carburant and _fold(c["carburant"]) != _fold(carburant):
            continue
        if marque and _fold(c["marque"]) != _fold(marque):
            continue
        if modele and _fold(c["modele"]) != _fold(modele):
            continue
        if prix_lt is not None and not c["prix"] < prix_lt:
            continue
        if prix_le is not None and not c["prix"] <= prix_le:
            continue
        if prix_gt is not None and not c["prix"] > prix_gt:
            continue
        if prix_ge is not None and not c["prix"] >= prix_ge:
            continue
        if km_lt is not None and not c["kilometrage"] < km_lt:
            continue
        if km_le is not None and not c["kilometrage"] <= km_le:
            continue
        out.append(c["id"])
    return sorted(out)


def ask(message: str, previous: dict | None = None, cars=None):
    """Envoie un message au chatbot réel ; renvoie (turn, identifiants triés des résultats)."""
    data = CARS if cars is None else cars
    vocab = VOCAB if cars is None else Vocabulary.from_cars(data)
    turn = process_message(message, previous or {}, data, vocab)
    return turn, sorted(c["id"] for c in filter_cars(data, turn.criteria))


def public(criteria: dict) -> dict:
    """Critères sans les indicateurs internes (ex. « _strict »)."""
    return {k: v for k, v in criteria.items() if not k.endswith("_strict")}


# ------------------------------------------------------------------ enregistrement des résultats obtenus

_EVIDENCE: dict[str, dict] = {}


class Evidence(dict):
    def __init__(self, test_id: str):
        super().__init__()
        self.test_id = test_id
        _EVIDENCE[test_id] = self

    def turn(self, turn, ids=None, cars=None):
        """Enregistre ce que l'application a réellement extrait et renvoyé."""
        data = {c["id"]: c for c in (CARS if cars is None else cars)}
        self["intent"] = turn.intent
        self["criteria"] = turn.criteria
        self["warnings"] = turn.warnings
        self["response"] = turn.response
        if ids is not None:
            self["result_count"] = len(ids)
            self["sample"] = [f'{i} {data[i]["marque"]} {data[i]["modele"]} {data[i]["ville"]} '
                              f'{data[i]["carburant"]} {data[i]["prix"]} DT {data[i]["kilometrage"]} km'
                              for i in ids[:4] if i in data]
        return self


@pytest.fixture
def evidence(request):
    m = re.match(r"test_([A-Z]{2})(\d{2})", request.node.name)
    test_id = f"{m.group(1)}-{m.group(2)}" if m else request.node.name
    ev = Evidence(test_id)
    ev["test"] = request.node.nodeid
    yield ev


def pytest_runtest_makereport(item, call):
    if call.when == "call":
        m = re.match(r"test_([A-Z]{2})(\d{2})", item.name)
        if m:
            tid = f"{m.group(1)}-{m.group(2)}"
            ev = _EVIDENCE.setdefault(tid, {"test": item.nodeid})
            ev["outcome"] = "passed" if call.excinfo is None else "failed"
            if call.excinfo is not None:
                ev["error"] = str(call.excinfo.value)[:900]


def pytest_runtest_logreport(report):
    if report.when == "setup" and report.skipped:
        m = re.search(r"test_([A-Z]{2})(\d{2})", report.nodeid)
        if m:
            _EVIDENCE.setdefault(f"{m.group(1)}-{m.group(2)}", {"test": report.nodeid})["outcome"] = "skipped"


def pytest_sessionfinish(session, exitstatus):
    if not _EVIDENCE:
        return
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"actual_{PHASE}.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    previous.update(_EVIDENCE)
    path.write_text(json.dumps(previous, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


# ------------------------------------------------------------------ application réelle (navigateur)


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def app_server():
    """Lance `streamlit run app.py` (application réelle, cars.json réel) sur un port dédié."""
    if _port_open(PORT):
        pytest.exit(f"Le port {PORT} est déjà utilisé : arrêtez l'ancien serveur de test.", returncode=3)
    log = open(RESULTS / f"streamlit_{PHASE}.log", "w", encoding="utf-8")  # noqa: SIM115 (fermé en fin de session)
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(PORT), "--server.headless",
         "true", "--browser.gatherUsageStats", "false", "--server.fileWatcherType", "none"],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(120):
        if _port_open(PORT):
            break
        time.sleep(0.5)
    else:
        proc.kill()
        pytest.fail("Le serveur Streamlit n'a pas démarré")
    yield BASE_URL
    proc.terminate()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()
    log.close()


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = None
        for channel in ("chrome", "msedge"):
            try:
                b = p.chromium.launch(channel=channel)
                break
            except Exception:  # noqa: BLE001
                continue
        if b is None:
            pytest.skip("Aucun navigateur Chromium (Chrome/Edge) disponible pour Playwright")
        yield b
        b.close()


@pytest.fixture
def page(browser, app_server):
    """Nouvelle session Streamlit (nouvel onglet = nouvelle conversation) ; erreurs JS collectées."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="fr-FR")
    pg = ctx.new_page()
    pg.console_errors = []
    pg.on("console", lambda m: m.type == "error" and pg.console_errors.append(m.text))
    pg.on("pageerror", lambda e: pg.console_errors.append(str(e)))
    pg.goto(app_server)
    pg.wait_for_selector(WELCOME, timeout=60000)
    wait_idle(pg)
    yield pg
    ctx.close()


# ------------------------------------------------------------------ actions dans le navigateur


def wait_idle(pg, timeout: float = 30) -> None:
    """Attend la fin de l'exécution du script Streamlit et la disparition de l'indicateur de saisie."""
    deadline = time.time() + timeout
    calm = 0
    while time.time() < deadline:
        state = pg.get_attribute('[data-testid="stApp"]', "data-test-script-state")
        busy = state == "running" or pg.locator(".am-typing").count() > 0
        calm = 0 if busy else calm + 1
        if calm >= 4:
            return
        time.sleep(0.15)
    raise AssertionError("L'application ne s'est pas stabilisée")


def assistant_count(pg) -> int:
    return pg.locator('[data-testid="stChatMessage"]').count()


def send(pg, text: str) -> None:
    """Tape un message dans le champ de conversation réel et attend la réponse de l'assistant."""
    before = assistant_count(pg)
    box = pg.get_by_test_id("stChatInputTextArea")
    box.click()
    box.fill(text)
    box.press("Enter")
    deadline = time.time() + 30
    while assistant_count(pg) < before + 2 and time.time() < deadline:
        time.sleep(0.1)
    wait_idle(pg)


def click(pg, locator) -> None:
    before = assistant_count(pg)
    locator.click()
    deadline = time.time() + 15
    while assistant_count(pg) == before and time.time() < deadline:
        time.sleep(0.1)
    wait_idle(pg)


def last_assistant(pg):
    return pg.locator('[data-testid="stChatMessage"]').last


def displayed_cards(pg, scope=None) -> list[dict]:
    """Cartes réellement affichées dans la dernière réponse : identifiant (clé du conteneur) + texte visible."""
    scope = scope or last_assistant(pg)
    cards = []
    loc = scope.locator('[class*="st-key-card_"]')
    for i in range(loc.count()):
        el = loc.nth(i)
        cls = el.get_attribute("class") or ""
        car_id = re.search(r"st-key-card_\d+_(\S+)", cls).group(1)
        cards.append({
            "id": car_id,
            "name": el.locator(".am-name").inner_text(),
            "meta": el.locator(".am-meta").inner_text(),
            "price_text": el.locator(".am-price").inner_text(),
            "chips": el.locator(".am-chips").inner_text(),
            "specs": el.locator(".am-specs").inner_text(),
        })
    return cards


def chip_locators(pg):
    """Une puce = un conteneur « st-key-chip_<msg>_<i> » (Streamlit y place deux boutons quand une info-bulle
    est définie) : on lit le premier bouton de chaque conteneur."""
    loc = pg.locator('[class*="st-key-chips_live"] [class*="st-key-chip_"]')
    return [loc.nth(i).locator("button").first for i in range(loc.count())]


def chip_labels(pg) -> list[str]:
    return [" ".join(b.inner_text().replace("✕", "").split()) for b in chip_locators(pg)]


def shot(pg, category: str, name: str, target=None) -> str:
    """Capture d'écran RÉELLE de l'application (Playwright). Phase « baseline » : suffixe _before."""
    suffix = "_before" if PHASE == "baseline" else ""
    folder = SCREENSHOTS / category
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}{suffix}.png"
    if target is not None:
        target.scroll_into_view_if_needed()
        time.sleep(0.4)
    pg.screenshot(path=str(path))
    return str(path.relative_to(TESTING)).replace("\\", "/")


def show_exchange(pg) -> None:
    """Fait défiler pour montrer la dernière question et le début de la réponse."""
    msgs = pg.locator('[data-testid="stChatMessage"]')
    n = msgs.count()
    if n >= 2:
        msgs.nth(n - 2).scroll_into_view_if_needed()
        pg.evaluate("(el) => el.scrollIntoView({block: 'start'})", msgs.nth(n - 2).element_handle())
    time.sleep(0.6)
