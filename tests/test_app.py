"""Tests de l'interface conversationnelle (Streamlit AppTest, sans navigateur).

Les résultats affichés dans le chat sont comparés à une recherche indépendante sur
cars.json : aucun résultat codé en dur.

Remarque : AppTest ne simule pas fidèlement un clic sur un bouton d'une réponse
ANCIENNE quand l'arbre des widgets a changé (le clic est attribué à un autre bouton).
Dans un vrai navigateur, ce cas fonctionne (vérifié avec Playwright, voir rapport_tests.md).
Ces tests cliquent donc uniquement sur les boutons de la dernière réponse.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from automind.search import filter_cars, load_dataset, sort_cars

HERE = Path(__file__).resolve().parent.parent
APP = str(HERE / "app.py")
CARS, _ = load_dataset(HERE / "data" / "cars.json")


def _start() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def _say(at: AppTest, text: str) -> None:
    at.chat_input(key="chat_msg").set_value(text).run()


def _buttons(at: AppTest, prefix: str) -> list:
    return [b for b in at.button if (b.key or "").startswith(prefix)]


def _last(at: AppTest) -> dict:
    return at.session_state.messages[-1]


def _expected_ids(criteria: dict, sort: str) -> list[str]:
    return [c["id"] for c in sort_cars(filter_cars(CARS, criteria), sort)]


def test_ecran_d_accueil_et_suggestion_cliquable():
    at = _start()
    assert not at.exception
    assert at.session_state.messages == []
    cards = _buttons(at, "welcome_")
    # Grille 2 × 2 : AppTest liste les boutons colonne par colonne, on compare donc l'ensemble.
    assert {b.label.split(maxsplit=1)[1] for b in cards} == {
        "Une voiture économique", "Une voiture automatique", "Une voiture à moins de 30 000 DT",
        "Une voiture disponible à Sfax"}
    next(b for b in cards if "Sfax" in b.label).click().run()
    assert at.session_state.criteria == {"ville": "Sfax"}
    msg = _last(at)
    assert msg["kind"] == "results"
    assert msg["ids"] == _expected_ids({"ville": "Sfax"}, msg["sort"])  # résultats réels, dans le chat
    assert not _buttons(at, "welcome_")  # l'accueil disparaît une fois la conversation lancée


def test_resultats_dans_la_conversation_et_suivi():
    at = _start()
    _say(at, "Je cherche une voiture diesel à Sfax.")
    _say(at, "Budget maximum 40 000 dinars.")
    msg = _last(at)
    assert at.session_state.criteria == {"ville": "Sfax", "carburant": "Diesel", "prix_max": 40000}
    assert msg["intent"] == "follow_up"
    assert msg["text"].startswith("D'accord, je limite la recherche à 40")
    assert msg["ids"] == _expected_ids(at.session_state.criteria, msg["sort"])
    shown = _buttons(at, "det_")
    assert len(shown) == len(msg["ids"]) + len(at.session_state.messages[1]["ids"][:6])  # cartes des 2 réponses
    assert not at.exception


def test_tri_par_la_conversation():
    at = _start()
    _say(at, "Je cherche une voiture diesel")
    _say(at, "Montre-moi des modèles plus récents")
    msg = _last(at)
    assert msg["intent"] == "sort"
    assert at.session_state.sort == "Année la plus récente"
    years = [next(c["annee"] for c in CARS if c["id"] == i) for i in msg["ids"]]
    assert years == sorted(years, reverse=True)
    assert at.session_state.criteria == {"carburant": "Diesel"}


def test_question_de_relance_prix_km_annee():
    at = _start()
    _say(at, "voiture à Tunis")
    ask = _buttons(at, "ask_")
    assert [b.label for b in ask] == ["💰 Le prix", "🛣️ Le kilométrage", "📅 L'année"]
    ask[1].click().run()
    assert at.session_state.sort == "Kilométrage croissant"
    assert at.session_state.messages[-2]["text"] == "privilégie le kilométrage"  # tracé dans le chat


def test_fiche_detaillee_dans_la_conversation():
    at = _start()
    _say(at, "Peugeot à Sfax")
    ids = _last(at)["ids"]
    _buttons(at, "det_")[0].click().run()
    msg = _last(at)
    assert msg["kind"] == "detail"
    assert msg["car_id"] == ids[0]
    assert len(msg["comparison"]) == 3                       # comparaison avec les autres résultats
    assert at.session_state.messages[-2]["text"].startswith("Voir les détails")
    _buttons(at, "close_")[0].click().run()                    # retour à la conversation
    # La fiche et la demande associée sont retirées. (AppTest peut ensuite rejouer un autre bouton,
    # voir l'en-tête du fichier : on vérifie donc seulement que la fiche a disparu.)
    assert all(m.get("kind") != "detail" for m in at.session_state.messages)
    assert not any(m["text"].startswith("Voir les détails") for m in at.session_state.messages if m["role"] == "user")


def test_puces_de_criteres_cliquables():
    at = _start()
    _say(at, "Je cherche une Peugeot ou une Renault à moins de 40 000 dinars")
    labels = [b.label for b in _buttons(at, "chip_")]
    assert labels == ["Peugeot  ✕", "Renault  ✕", "Budget < 40 000 DT  ✕"]  # « moins de » : borne stricte
    _buttons(at, "chip_")[1].click().run()                     # retire seulement Renault
    assert at.session_state.criteria == {"marque": "Peugeot", "prix_max": 40000, "prix_max_strict": True}


def test_aucun_resultat_et_pistes_d_elargissement():
    at = _start()
    _say(at, "électrique à Gabès moins de 20000 DT")
    msg = _last(at)
    assert msg["ids"] == []
    relax = _buttons(at, "relax_")
    assert relax, "des pistes d'élargissement doivent être proposées"
    before = dict(at.session_state.criteria)
    relax[0].click().run()
    assert at.session_state.criteria != before
    assert _last(at)["ids"]                                   # la piste choisie donne des résultats


def test_afficher_plus_reste_dans_la_conversation():
    at = _start()
    _say(at, "voiture à Tunis")
    n_cards = len(_buttons(at, "det_"))
    _buttons(at, "more_")[0].click().run()
    assert len(_buttons(at, "det_")) == n_cards + 6
    assert len(at.session_state.messages) == 2                # aucun nouveau message, pas de page séparée


def test_nouvelle_conversation():
    at = _start()
    _say(at, "diesel")
    next(b for b in at.button if b.key == "new_conv").click().run()
    assert at.session_state.messages == []
    assert at.session_state.criteria == {}
    assert _buttons(at, "welcome_")


def test_filtres_manuels_affichent_le_resultat_dans_le_chat():
    at = _start()
    _say(at, "Peugeot à Tunis")
    assert at.selectbox(key="mf_ville").value == "Tunis"       # le panneau reflète le chat
    at.selectbox(key="mf_ville").set_value("Sfax")
    next(b for b in at.button if b.label == "Appliquer dans la conversation").click().run()
    assert at.session_state.criteria == {"marque": "Peugeot", "ville": "Sfax"}
    assert at.session_state.messages[-2]["text"].startswith("Filtres manuels")
    assert _last(at)["ids"] == _expected_ids(at.session_state.criteria, _last(at)["sort"])
