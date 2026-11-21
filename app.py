"""AutoMind AI — assistant conversationnel de recherche automobile (Streamlit).

Une seule page : la conversation. Les résultats (cartes véhicules), les critères,
les suggestions et les fiches détaillées sont affichés DANS les messages de l'assistant.

Lancement : streamlit run app.py   (ou scripts/lancer.bat / scripts/lancer.sh)
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st

from automind import ui
from automind.chatbot import (
    CRITERIA_LABELS,
    YEAR_KEYS,
    Vocabulary,
    describe_criteria,
    format_value,
    process_message,
)
from automind.search import (
    DEFAULT_SORT,
    REMOVAL_MESSAGES,
    clean_records,
    compare_to,
    dataset_stats,
    filter_cars,
    highlight_badges,
    load_dataset,
    sort_cars,
    suggest_followups,
    suggest_relaxations,
)

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "cars.json"
PAGE_SIZE = 6            # cartes affichées par réponse (puis « Afficher plus »)
TYPING_DELAY = 0.55      # durée minimale de l'indicateur « je recherche… » (secondes), pour qu'il soit perceptible
ALL = "Toutes"
ASSISTANT_AVATAR = ":material/directions_car:"
WELCOME_SUGGESTIONS = [
    ("🚗  Une voiture économique", "Je cherche une voiture économique"),
    ("⚡  Une voiture automatique", "Je veux une voiture automatique"),
    ("💰  Une voiture à moins de 30 000 DT", "Une voiture à moins de 30 000 DT"),
    ("📍  Une voiture disponible à Sfax", "Une voiture disponible à Sfax"),
]
ASK_SORT = [("💰 Le prix", "privilégie le prix"), ("🛣️ Le kilométrage", "privilégie le kilométrage"),
            ("📅 L'année", "privilégie l'année")]

st.set_page_config(page_title="AutoMind AI — Assistant automobile", page_icon="🚗", layout="wide",
                   initial_sidebar_state="collapsed")


# ------------------------------------------------------------------ données

@st.cache_data(show_spinner=False)
def get_data(path: str, mtime: float) -> tuple[list[dict], dict, str | None]:
    """Charge cars.json ; s'il est absent, génère la base par défaut en mémoire."""
    try:
        cars, meta = load_dataset(path)
        cars, rejected = clean_records(cars)  # une annonce mal formée est écartée, l'application continue
        notice = (f"{rejected} annonce{'s' if rejected > 1 else ''} mal formée{'s' if rejected > 1 else ''} "
                  f"(champ manquant ou invalide) ignorée{'s' if rejected > 1 else ''}.") if rejected else None
        return cars, meta, notice
    except FileNotFoundError:
        from automind.generate_cars import build_document, generate_dataset
        doc = build_document(generate_dataset(200, 42), 42)
        return doc["cars"], doc["metadata"], "cars.json introuvable : base de démonstration générée en mémoire (graine 42)."


@st.cache_resource(show_spinner=False)
def get_vocab(path: str, mtime: float) -> Vocabulary:
    return Vocabulary.from_cars(get_data(path, mtime)[0])


mtime = DATA_PATH.stat().st_mtime if DATA_PATH.exists() else 0.0
try:
    CARS, META, DATA_NOTICE = get_data(str(DATA_PATH), mtime)
    VOCAB = get_vocab(str(DATA_PATH), mtime)
except (json.JSONDecodeError, KeyError, TypeError) as exc:
    st.error(f"Impossible de lire cars.json ({exc}). Régénérez-le avec : python -m automind.generate_cars")
    st.stop()
CARS_BY_ID = {c["id"]: c for c in CARS}
STATS = dataset_stats(CARS)

ss = st.session_state


# ------------------------------------------------------------------ état de la conversation

def _now() -> str:
    return datetime.now().strftime("%H:%M")


def sync_manual_widgets(criteria: dict) -> None:
    """Le panneau manuel reflète les critères actifs (une seule source de vérité)."""
    def single(key: str):
        value = criteria.get(key, ALL)
        return value if not isinstance(value, list) else ALL  # plusieurs valeurs : affichées dans le chat
    ss.mf_ville, ss.mf_carburant, ss.mf_marque = single("ville"), single("carburant"), single("marque")
    ss.mf_categorie, ss.mf_boite = single("categorie"), single("boite")
    ss.mf_prix, ss.mf_km = criteria.get("prix_max"), criteria.get("kilometrage_max")
    ss.mf_annee_min, ss.mf_annee_max = criteria.get("annee_min", ALL), criteria.get("annee_max", ALL)


def init_state(force: bool = False) -> None:
    if force or "messages" not in ss:
        ss.messages = []
        ss.criteria = {}
        ss.sort = DEFAULT_SORT
        ss.history = []
        ss.scrolled = 0
        sync_manual_widgets({})


def queue(job: dict) -> None:
    """Toute action (message, suggestion, détail) est traitée au prochain affichage,
    avec l'indicateur « je recherche… »."""
    ss.job = job


def queue_message(text: str, fresh: bool = False) -> None:
    queue({"type": "message", "text": text, "fresh": fresh})


def _labels(added: dict, changed: dict, removed: dict) -> tuple[list, list, list]:
    changed_items = [(CRITERIA_LABELS[k], f"{format_value(k, old)} → {format_value(k, new)}")
                     for k, (old, new) in changed.items() if k not in YEAR_KEYS]
    if any(k in YEAR_KEYS for k in changed):
        changed_items += [(label, v) for label, v in describe_criteria({k: new for k, (_, new) in changed.items()})
                          if label.startswith("Ann")]
    return describe_criteria(added), changed_items, [label for label, _ in describe_criteria(removed)]


def results_message(text: str, intent: str, criteria: dict, warnings: list[str] | None = None,
                    added: dict | None = None, changed: dict | None = None, removed: dict | None = None,
                    title: str | None = None) -> dict:
    """Message de l'assistant contenant les résultats RÉELS de la recherche (identifiants triés)."""
    ids = [c["id"] for c in sort_cars(filter_cars(CARS, criteria), ss.sort)]
    a, c, r = _labels(added or {}, changed or {}, removed or {})
    return {"role": "assistant", "kind": "results", "intent": intent, "title": title, "text": text,
            "criteria": dict(criteria), "ids": ids, "sort": ss.sort, "limit": PAGE_SIZE,
            "warnings": warnings or [], "added": a, "changed": c, "removed": r, "time": _now()}


def handle_message(text: str, fresh: bool = False) -> None:
    text = (text or "").strip()
    if not text:
        return
    previous = {} if fresh else ss.criteria
    turn = process_message(text, previous, CARS, VOCAB)
    ss.messages.append({"role": "user", "text": text, "time": _now()})
    if turn.sort:
        ss.sort = turn.sort
    elif turn.intent == "reset" or (turn.intent == "search" and not previous):
        ss.sort = DEFAULT_SORT
    ss.criteria = turn.criteria
    if turn.intent in ("search", "follow_up", "sort", "no_criteria"):
        ss.messages.append(results_message(turn.response, turn.intent, turn.criteria, turn.warnings,
                                           turn.added, turn.changed, turn.removed))
    else:  # reset, aide, ambiguïté, hors périmètre : réponse textuelle + pistes
        ss.messages.append({"role": "assistant", "kind": "text", "intent": turn.intent, "text": turn.response,
                            "warnings": turn.warnings, "criteria": dict(turn.criteria), "time": _now()})
    ss.history.append(text)
    sync_manual_widgets(ss.criteria)


def handle_detail(car_id: str, ref: int) -> None:
    car = CARS_BY_ID[car_id]
    context = [CARS_BY_ID[i] for i in ss.messages[ref].get("ids", []) if i in CARS_BY_ID]
    ss.messages.append({"role": "user", "text": f"Voir les détails : {car['marque']} {car['modele']} "
                                                f"({car['id']})", "time": _now()})
    ss.messages.append({"role": "assistant", "kind": "detail", "intent": "detail", "car_id": car_id,
                        "text": f"Voici la fiche complète de la {car['marque']} {car['modele']}.",
                        "comparison": compare_to(car, context), "time": _now()})


def run_job(job: dict) -> None:
    if job["type"] == "message":
        handle_message(job["text"], job.get("fresh", False))
    elif job["type"] == "detail":
        handle_detail(job["id"], job["ref"])


# ------------------------------------------------------------------ rappels des boutons

def on_new_conversation() -> None:
    init_state(force=True)


def on_more(mi: int) -> None:
    ss.messages[mi]["limit"] += PAGE_SIZE


def on_close_detail(mi: int) -> None:
    """Ferme la fiche : retire la fiche et la demande associée, la conversation reprend."""
    if mi < len(ss.messages) and ss.messages[mi].get("kind") == "detail":
        del ss.messages[mi]
        if mi - 1 >= 0 and ss.messages[mi - 1]["role"] == "user":
            del ss.messages[mi - 1]
    ss.scrolled = len(ss.messages)


def on_apply_manual() -> None:
    new: dict = {}
    for key, widget in (("ville", "mf_ville"), ("carburant", "mf_carburant"), ("marque", "mf_marque"),
                        ("categorie", "mf_categorie"), ("boite", "mf_boite"),
                        ("annee_min", "mf_annee_min"), ("annee_max", "mf_annee_max")):
        if ss[widget] != ALL:
            new[key] = ss[widget]
        elif isinstance(ss.criteria.get(key), list):
            new[key] = ss.criteria[key]  # valeur multiple définie dans le chat : conservée
    for key, widget in (("prix_max", "mf_prix"), ("kilometrage_max", "mf_km")):
        if ss[widget]:
            new[key] = int(ss[widget])
            if new[key] == ss.criteria.get(key) and ss.criteria.get(f"{key}_strict"):
                new[f"{key}_strict"] = True  # borne inchangée : « moins de » reste strict
    for key in ("prix_min", "prix_min_strict", "kilometrage_min", "kilometrage_min_strict"):
        if key in ss.criteria:
            new[key] = ss.criteria[key]  # minimums définis dans le chat (pas de champ manuel) : conservés
    model = ss.criteria.get("modele")
    if model and new.get("marque") and model in VOCAB.models_of(new["marque"]):
        new["modele"] = model
    old = ss.criteria
    added = {k: v for k, v in new.items() if k not in old}
    changed = {k: (old[k], v) for k, v in new.items() if k in old and old[k] != v}
    removed = {k: v for k, v in old.items() if k not in new}
    if not (added or changed or removed):
        return
    n = len(filter_cars(CARS, new))
    summary = ", ".join(f"{label} = {v}" for label, v in describe_criteria(new)) or "aucun critère"
    ss.messages.append({"role": "user", "text": f"Filtres manuels : {summary}", "time": _now()})
    if n:
        text = f"J'ai appliqué vos filtres manuels : {n} voiture(s) correspondent."
    else:
        text = "J'ai appliqué vos filtres manuels, mais aucune voiture ne correspond."
    ss.messages.append(results_message(text, "follow_up", new, [], added, changed, removed,
                                       title="Filtres manuels"))
    ss.criteria = new
    sync_manual_widgets(new)


# ------------------------------------------------------------------ rendu des messages

def live_chips(criteria: dict) -> list[tuple[str, str]]:
    """Puces cliquables de la dernière réponse : (libellé, message qui retire le critère)."""
    # Valeur d'un critère multiple (« Peugeot ou Renault ») : « enlève Peugeot » ne retire que celle-ci.
    return [(f"{text}  ✕", f"enlève {single}" if single else REMOVAL_MESSAGES[key])
            for key, text, single in ui.chip_items(criteria)]


def _button_row(key: str, items: list[tuple[str, str]]) -> None:
    """Rangée de pastilles : chaque clic envoie un message visible dans la conversation."""
    with st.container(key=key, horizontal=True):
        for i, (label, message) in enumerate(items):
            st.button(label, key=f"{key}_{i}", on_click=queue_message, args=(message,), help=f"Envoie « {message} »")


def _render_criteria(mi: int, msg: dict, is_last: bool) -> None:
    chips = live_chips(msg["criteria"]) if is_last else []
    if chips:  # dernière réponse : puces cliquables (retrait d'un critère)
        st.markdown('<div class="am-crit-row"><span class="am-crit-label">🔎 Recherche — cliquez pour retirer un '
                    'critère :</span></div>', unsafe_allow_html=True)
        with st.container(key="chips_live", horizontal=True):
            for i, (label, message) in enumerate(chips):
                st.button(label, key=f"chip_{mi}_{i}", on_click=queue_message, args=(message,),
                          help=f"Envoie « {message} »")
    else:  # réponses précédentes : critères figés tels qu'ils étaient à ce moment
        st.markdown(ui.criteria_row_html(msg["criteria"]), unsafe_allow_html=True)
    # Les changements (+ ajouté, ⇄ modifié, retiré) ne sont utiles que lorsqu'une recherche est modifiée.
    changes = "" if msg["intent"] == "search" else ui.changes_html(msg["added"], msg["changed"], msg["removed"])
    extra = changes + ui.warnings_html(msg["warnings"])
    if extra:
        st.markdown(extra, unsafe_allow_html=True)


def _render_cards(mi: int, msg: dict, cars: list[dict]) -> None:
    badges = highlight_badges(cars)
    st.markdown(ui.summary_html(cars, msg["sort"]), unsafe_allow_html=True)
    with st.container(key=f"carousel_{mi}", horizontal=True):
        for car in cars[:msg["limit"]]:
            with st.container(key=f"card_{mi}_{car['id']}"):
                st.markdown(ui.car_card_html(car, msg["criteria"], badges.get(car["id"])), unsafe_allow_html=True)
                st.button("Voir les détails", key=f"det_{mi}_{car['id']}", on_click=queue,
                          args=({"type": "detail", "id": car["id"], "ref": mi},))
    remaining = len(cars) - msg["limit"]
    if remaining > 0:
        st.button(f"Afficher {min(PAGE_SIZE, remaining)} voitures de plus ({remaining} restantes)",
                  key=f"more_{mi}", on_click=on_more, args=(mi,))


def _render_next_steps(mi: int, msg: dict, n: int) -> None:
    """Question de relance et pistes d'affinage (dernière réponse uniquement)."""
    if n < 2:
        return
    st.markdown('<div class="am-ask">Voulez-vous que je privilégie le prix, le kilométrage ou l\'année ?</div>',
                unsafe_allow_html=True)
    _button_row(f"ask_{mi}", ASK_SORT)
    followups = suggest_followups(CARS, msg["criteria"]) if msg["criteria"] else []
    if followups:
        st.markdown('<div class="am-mini">Affiner la recherche</div>', unsafe_allow_html=True)
        _button_row(f"actions_{mi}", [(f"{s['label']} · {s['count']}", s["message"]) for s in followups])


def render_results(mi: int, msg: dict, is_last: bool) -> None:
    st.markdown(ui.answer_head_html(msg["intent"], msg["text"], msg.get("title")), unsafe_allow_html=True)
    _render_criteria(mi, msg, is_last)
    cars = [CARS_BY_ID[i] for i in msg["ids"] if i in CARS_BY_ID]
    if cars:
        _render_cards(mi, msg, cars)
        if is_last:
            _render_next_steps(mi, msg, len(cars))
        return
    st.markdown(ui.empty_html(), unsafe_allow_html=True)
    relax = suggest_relaxations(CARS, msg["criteria"]) if is_last else []
    if relax:
        _button_row(f"relax_{mi}", [(f"{s['label']} · {s['count']}", s["message"]) for s in relax])


def render_text(mi: int, msg: dict, is_last: bool) -> None:
    st.markdown(ui.answer_head_html(msg["intent"], msg["text"]) + ui.criteria_row_html(msg.get("criteria", {}))
                + ui.warnings_html(msg.get("warnings", [])), unsafe_allow_html=True)
    if is_last:
        st.markdown('<div class="am-mini">Pour commencer</div>', unsafe_allow_html=True)
        _button_row(f"starters_{mi}", [(label.replace("  ", " "), message) for label, message in WELCOME_SUGGESTIONS])


def render_detail(mi: int, msg: dict) -> None:
    car = CARS_BY_ID.get(msg["car_id"])
    st.markdown(ui.answer_head_html("detail", msg["text"]), unsafe_allow_html=True)
    if car:
        st.markdown(ui.detail_html(car, msg.get("comparison", [])), unsafe_allow_html=True)
    with st.container(key=f"actions_detail_{mi}", horizontal=True):
        st.button("↩ Fermer la fiche et revenir à la conversation", key=f"close_{mi}", on_click=on_close_detail,
                  args=(mi,))


def render_conversation() -> None:
    last_assistant = max((i for i, m in enumerate(ss.messages) if m["role"] == "assistant"), default=-1)
    for mi, msg in enumerate(ss.messages):
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(f'{escape(msg["text"])}{ui.time_html(msg.get("time", ""))}', unsafe_allow_html=True)
            continue
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            if msg["kind"] == "results":
                render_results(mi, msg, mi == last_assistant)
            elif msg["kind"] == "detail":
                render_detail(mi, msg)
            else:
                render_text(mi, msg, mi == last_assistant)
            st.markdown(ui.time_html(msg.get("time", "")), unsafe_allow_html=True)


def scroll_to_latest() -> None:
    """Défilement doux vers le dernier échange (question + début de la réponse).
    Sur l'écran d'accueil, ramène la page en haut (Streamlit fait défiler les pages de chat vers le bas)."""
    target = len(ss.messages) if ss.messages else -1
    if ss.scrolled == target:
        return
    ss.scrolled = target
    if ss.messages:
        script = ("const m=d.querySelectorAll('[data-testid=\"stChatMessage\"]');if(!m.length)return;"
                  "const t=m.length>1?m[m.length-2]:m[m.length-1];t.scrollIntoView({behavior:'smooth',block:'start'});")
    else:
        script = "const t=d.querySelector('.st-key-topbar');if(t)t.scrollIntoView({behavior:'smooth',block:'start'});"
    with st.container(key="scroller"):
        # Plusieurs tentatives : le défilement automatique de Streamlit peut reprendre la main juste après.
        st.iframe(f"<html><body><script>function go(){{const d=window.parent.document;{script}}}"
                  "[250,800,1500].forEach(function(ms){setTimeout(go,ms);});</script></body></html>", height=1)


# ------------------------------------------------------------------ page

init_state()
st.markdown(ui.CSS, unsafe_allow_html=True)

with st.container(key="topbar"):
    top_l, top_r = st.columns([4, 1.7], vertical_alignment="center")
    top_l.markdown(ui.top_bar_html(), unsafe_allow_html=True)
    top_r.button("＋ Nouvelle conversation", key="new_conv", on_click=on_new_conversation, use_container_width=True)
if DATA_NOTICE:
    st.info(DATA_NOTICE)

prompt = st.chat_input("Décrivez la voiture que vous recherchez...", key="chat_msg")
job = ss.pop("job", None)
if prompt and prompt.strip():
    job = {"type": "message", "text": prompt}

if not ss.messages and not job:
    st.markdown(ui.welcome_html(STATS["total"], len(STATS["brands"]), len(STATS["cities"])), unsafe_allow_html=True)
    with st.container(key="welcome_cards"):
        cols = st.columns(2)
        for i, (label, message) in enumerate(WELCOME_SUGGESTIONS):
            cols[i % 2].button(label, key=f"welcome_{i}", on_click=queue_message, args=(message,),
                               use_container_width=True)

render_conversation()

if job:
    if job["type"] == "message":
        with st.chat_message("user"):
            st.markdown(escape(job["text"]))
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.markdown(ui.typing_html(), unsafe_allow_html=True)
        started = time.monotonic()
        run_job(job)
        time.sleep(max(0.0, TYPING_DELAY - (time.monotonic() - started)))
    st.rerun()

scroll_to_latest()

# ------------------------------------------------------------------ barre latérale (secondaire)

with st.sidebar:
    st.markdown("### AutoMind AI")
    st.button("Nouvelle conversation", on_click=on_new_conversation, use_container_width=True, key="side_new")

    with st.expander("Filtres manuels (optionnel)"):
        st.markdown('<div class="am-side-note">La conversation reste l\'outil principal. Ces filtres '
                    "<b>remplacent les critères actifs</b> et le résultat s'affiche dans le chat.</div>",
                    unsafe_allow_html=True)
        with st.form("manual_filters", border=False):
            st.selectbox("Ville", [ALL] + STATS["cities"], key="mf_ville")
            st.selectbox("Carburant", [ALL] + list(STATS["fuels"]), key="mf_carburant")
            st.selectbox("Marque", [ALL] + STATS["brands"], key="mf_marque")
            st.selectbox("Catégorie", [ALL] + list(STATS["categories"]), key="mf_categorie")
            st.selectbox("Boîte", [ALL, "Manuelle", "Automatique"], key="mf_boite")
            st.number_input("Prix maximum (DT)", min_value=0, step=1000, key="mf_prix", placeholder="Sans limite")
            st.number_input("Kilométrage maximum (km)", min_value=0, step=5000, key="mf_km", placeholder="Sans limite")
            y1, y2 = st.columns(2)
            y1.selectbox("Année min.", [ALL] + STATS["years"], key="mf_annee_min")
            y2.selectbox("Année max.", [ALL] + STATS["years"], key="mf_annee_max")
            st.form_submit_button("Appliquer dans la conversation", type="primary", on_click=on_apply_manual,
                                  use_container_width=True)

    with st.expander("Historique des recherches"):
        if not ss.history:
            st.caption("Aucune recherche pour le moment.")
        for i, q in enumerate(reversed(ss.history[-8:])):
            st.button(q, key=f"hist_{i}_{q}", on_click=queue_message, args=(q, True), use_container_width=True)

    with st.expander("Statistiques de la base"):
        st.markdown(f"**{STATS['total']} véhicules** · {len(STATS['brands'])} marques · {len(STATS['cities'])} villes")
        st.markdown(f"Prix : {format_value('prix_max', STATS['price_min'])} – "
                    f"{format_value('prix_max', STATS['price_max'])} (moyenne "
                    f"{format_value('prix_max', STATS['price_avg'])})")
        st.markdown(ui.bars_html(STATS["fuels"], STATS["total"]), unsafe_allow_html=True)

    with st.expander("Données et fonctionnement"):
        st.markdown(f"- Données **synthétiques et fictives** ({META.get('count', STATS['total'])} annonces, graine "
                    f"`{META.get('seed', '—')}`) ; les prix ne sont pas des cotes du marché.\n"
                    "- Analyse des messages **par règles** (expressions régulières et vocabulaire issu de la base) : "
                    "aucun modèle de langage, aucune API, fonctionnement hors ligne.\n"
                    "- Ce qui n'est pas compris est signalé, jamais deviné.")
