"""Moteur conversationnel d'Findrive Assistant.

Analyse PAR RÈGLES (expressions régulières + vocabulaire extrait de la base).
Aucun modèle de langage, aucune API externe, aucune donnée envoyée sur Internet.

Point d'entrée : `process_message(message, criteres_precedents, voitures)`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field

from .catalog import BRANDS
from .search import filter_cars

# ---------------------------------------------------------------- présentation

CRITERIA_LABELS = {
    "marque": "Marque",
    "modele": "Modèle",
    "ville": "Ville",
    "carburant": "Carburant",
    "categorie": "Catégorie",
    "boite": "Boîte",
    "prix_max": "Prix maximum",
    "prix_min": "Prix minimum",
    "kilometrage_max": "Kilométrage maximum",
    "kilometrage_min": "Kilométrage minimum",
    "annee_min": "Année minimum",
    "annee_max": "Année maximum",
}
YEAR_KEYS = ("annee_min", "annee_max")
PRICE_KEYS = ("prix_max", "prix_min")
KM_KEYS = ("kilometrage_max", "kilometrage_min")
BOUND_KEYS = PRICE_KEYS + KM_KEYS
STRICT_SUFFIX = "_strict"  # « prix_max_strict » = True : « moins de 40 000 DT » exclut 40 000 DT


def format_int(n: int) -> str:
    return f"{int(n):,}".replace(",", " ")


def format_price(n: int) -> str:
    return f"{format_int(n)} DT"


def format_km(n: int) -> str:
    return f"{format_int(n)} km"


def format_value(key: str, value) -> str:
    if isinstance(value, (list, tuple)):
        return " ou ".join(str(v) for v in value)
    if key in PRICE_KEYS:
        return format_price(value)
    if key in KM_KEYS:
        return format_km(value)
    return str(value)


def bound_text(key: str, criteria: dict) -> str:
    """Valeur affichée d'un critère ; une borne stricte est préfixée : « < 40 000 DT », « > 30 000 DT »."""
    text = format_value(key, criteria[key])
    if key in BOUND_KEYS and criteria.get(key + STRICT_SUFFIX):
        return ("< " if key.endswith("_max") else "> ") + text
    return text


def describe_criteria(criteria: dict) -> list[tuple[str, str]]:
    """Liste ordonnée (libellé, valeur) ; les bornes d'année sont regroupées."""
    out = [(CRITERIA_LABELS[k], bound_text(k, criteria))
           for k in CRITERIA_LABELS if k not in YEAR_KEYS and criteria.get(k) is not None]
    lo, hi = criteria.get("annee_min"), criteria.get("annee_max")
    if lo is not None and hi is not None:
        out.append(("Année", str(lo)) if lo == hi else ("Années", f"{lo} – {hi}"))
    elif lo is not None:
        out.append(("Année minimum", str(lo)))
    elif hi is not None:
        out.append(("Année maximum", str(hi)))
    return out


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n > 1 else ''}"


# ---------------------------------------------------------------- normalisation

def normalize(text: str) -> str:
    """Minuscules, sans accents, ponctuation simplifiée.
    La longueur est conservée (1 caractère -> 1 caractère) pour pouvoir
    retrouver le texte original à partir d'une position."""
    out = []
    for ch in text:
        low = ch.lower()
        c = low if len(low) == 1 else ch
        c = unicodedata.normalize("NFD", c)[0]
        if c in "’‘`´":
            c = "'"
        elif c in "-–—_/" or c.isspace():
            c = " "
        out.append(c)
    return "".join(out)


def _word_pattern(name: str) -> str:
    parts = normalize(name).split()
    return r"(?<![\w])" + r"\s+".join(re.escape(p) for p in parts) + r"(?![\w])"


# ---------------------------------------------------------------- vocabulaire

FUEL_PATTERNS = {
    "Diesel": r"\b(diesel|gasoil|gazole|gas oil)\b",
    "Essence": r"\b(essence|sans plomb|benzine)\b",
    "Hybride": r"\bhybrides?\b",
    "Électrique": r"\b(electriques?|100 ?% electrique)\b",
}
CATEGORY_PATTERNS = {
    "SUV": r"\b(suvs?|4x4|crossovers?)\b",
    "Berline": r"\bberlines?\b",
    "Citadine": r"\b(citadines?|petites? voitures?)\b",
    "Compacte": r"\bcompactes?\b",
}
TRANSMISSION_PATTERNS = {
    "Automatique": r"\b(automatiques?|boite auto|bva)\b",
    "Manuelle": r"\b(manuelles?|boite meca\w*|bvm)\b",
}
BRAND_ALIASES = {
    "vw": "Volkswagen", "volks": "Volkswagen", "mercedes benz": "Mercedes", "mercedes-benz": "Mercedes",
    "citroen": "Citroën", "renaut": "Renault", "peugot": "Peugeot", "toyta": "Toyota",
}
OTHER_BRANDS = [
    "tesla", "jeep", "suzuki", "chery", "mazda", "honda", "mitsubishi", "isuzu", "mahindra", "geely",
    "mg", "porsche", "volvo", "jaguar", "land rover", "lexus", "alfa romeo", "mini", "chevrolet",
    "haval", "cupra", "ds", "byd", "subaru", "lada",
]
OTHER_CITIES = [
    "paris", "tozeur", "jendouba", "beja", "le kef", "gafsa", "zaghouan", "siliana", "kasserine",
    "medenine", "tataouine", "kebili", "sidi bouzid", "manouba", "ben arous", "djerba", "hammamet",
    "zarzis", "lyon", "marseille", "alger", "tripoli",
]

# Préférences sans valeur précise : traduites en ORDRE DE TRI (jamais en filtre inventé).
SORT_PATTERNS = {
    "Prix décroissant": r"\b(plus chere?s?|les plus chers|prix decroissant)\b",
    "Prix croissant": r"\b(moins chere?s?|pas (trop )?chere?s?|economiques?|bon marche|petit prix|abordables?|"
                      r"prix bas|privilegi\w* le prix|tri\w* par prix|par prix|prix croissant|meilleur prix)\b",
    "Année la plus récente": r"\b(plus recente?s?|recente?s?|plus neuve?s?|neuve?s?|derniers modeles|"
                             r"pas (trop )?vieille?s?|privilegi\w* l'annee|tri\w* par annee|par annee)\b",
    "Kilométrage croissant": r"\b(moins kilometree?s?|peu kilometree?s?|faible kilometrage|moins de kilometres|"
                             r"pas beaucoup de (km|kilometres)|privilegi\w* le kilometrage|tri\w* par kilometrage|"
                             r"par kilometrage|kilometrage croissant)\b",
}

VAGUE_TERMS = [
    (r"\b(augmente\w*|baisse\w*|reduis\w*|diminue\w*|monte\w*|change\w*)\s+(le |mon |la |ma )?(budget|prix)\b",
     "prix_max", "Quel nouveau budget souhaitez-vous ? Par exemple : « augmente le budget à 50 000 DT »."),
    (r"\b(augmente\w*|baisse\w*|reduis\w*|diminue\w*|change\w*)\s+(le |mon )?kilometrage\b", "kilometrage_max",
     "Quel kilométrage maximum souhaitez-vous ? Par exemple : « moins de 120 000 km »."),
    (r"\b(grande?s?|spacieuse?s?|familiale?s?)\b", "categorie",
     "« {m} » ne correspond pas à une catégorie précise. Essayez : SUV ou berline."),
    (r"\b(luxe|luxueuse?s?|haut de gamme|premium|prestige)\b", "marque",
     "« {m} » n'est pas une marque. Les marques premium de la base sont BMW, Mercedes et Audi."),
    (r"\b(rouges?|noire?s?|blanche?s?|blancs?|grise?s?|bleue?s?|couleurs?)\b", None,
     "La couleur (« {m} ») n'est pas renseignée dans les annonces : ce critère est ignoré."),
    (r"\b(gpl|gnv|gaz naturel|hydrogene|ethanol|bioethanol|e85|flex ?fuel)\b", None,
     "Le carburant « {m} » n'est pas disponible dans la base (Essence, Diesel, Hybride, Électrique) : "
     "critère ignoré."),
    (r"\b(toit ouvrant|gps|cuir|climatisation|clim|puissance|chevaux|places|portes|bon etat)\b", None,
     "« {m} » n'est pas renseigné dans la base : ce critère est ignoré."),
]

RESET_RE = re.compile(
    r"\b(nouvelle recherche|reinitialis\w*|recommenc\w*|"
    r"oublie\w* (tout|les criteres|mes criteres|la recherche|les filtres|ce que)|"
    r"efface\w* (tout|les criteres|mes criteres|les filtres|la recherche)|tout effacer|reset|"
    r"remise a zero|repartir de zero|on repart de zero)\b")
HELP_RE = re.compile(r"^\s*(bonjour|bonsoir|salut|hello|coucou|aide|help|merci|comment (ca marche|t'utiliser)|"
                     r"que (sais|peux) tu faire)\b")
UNSUPPORTED_RE = re.compile(r"\b(louer|location|vendre|revendre|reparer|reparation|assurances?|credits?|leasing|"
                            r"motos?|scooters?|camions?|pieces? detachees?|mecanicien|garage)\b")
SEARCH_RE = re.compile(r"\b(je cherche|je recherche|cherche|recherche|je veux|je voudrais|j'aimerais|"
                       r"il me faut|trouve moi|trouvez|montre moi|montrez|affiche|propose|besoin d)|"
                       r"^\s*(une? )?(voiture|vehicule|auto)s?\b")
FOLLOW_RE = re.compile(r"^\s*(et|mais|plutot|seulement|uniquement|aussi|egalement|maintenant|avec|sans|"
                       r"ajoute|rajoute|enleve|retire|finalement|par contre|pareil|ok|d'accord|augmente\w*|"
                       r"baisse\w*|passe|monte|elargi\w*|change\w*|modifie\w*|je prefere)\b|"
                       r"\b(seulement|uniquement|plutot|aussi|egalement|en plus|parmi (elles|eux|ces)|"
                       r"precedente?|meme recherche|affine\w*)\b")
CAR_WORD_RE = re.compile(r"\b(voitures?|vehicules?|autos?|annonces?|occasions?|bagnoles?|tout|toutes|modeles?)\b")
# « Enlève le critère diesel », « retire Sfax » : les valeurs citées sont RETIRÉES au lieu d'être ajoutées.
REMOVE_VALUE_RE = re.compile(r"\b(enleve\w*|enlever|retire\w*|supprime\w*|oublie\w*|exclu\w*)\b")
TEXT_KEYS = ("marque", "modele", "ville", "carburant", "categorie", "boite")

REMOVAL_RE = re.compile(
    r"(peu importe|n'importe quel(?:le)?s?|quel(?:le)?s? que soit|"
    r"sans (?:limite|contrainte|critere|filtre|preference)\s+(?:de |d'|sur )?|"
    r"retire\w*|enleve\w*|supprime\w*|oublie\w*|toutes les|tous les)\s*"
    r"(?:la |le |les |l'|de |du )?"
    r"(villes?|carburants?|motorisations?|energie|marques?|modeles?|prix|budget|kilometrages?|km|"
    r"annees?|categories?|types?|boites?|transmissions?)\b")
# « sans prix minimum », « peu importe le kilométrage minimum » : retire seulement la borne basse.
REMOVAL_MIN_RE = re.compile(r"\b(?:sans|peu importe (?:le |du )?|pas de)\s*(?:(prix|budget|kilometrage|km)\s+minimum|"
                            r"minimum\s+(?:de |d')?(prix|budget|kilometrage|km))\b")
REMOVAL_KEYS = {
    "ville": ["ville"], "carburant": ["carburant"], "motorisation": ["carburant"], "energie": ["carburant"],
    "marque": ["marque", "modele"], "modele": ["modele"], "prix": ["prix_max", "prix_min"],
    "budget": ["prix_max", "prix_min"], "kilometrage": ["kilometrage_max", "kilometrage_min"],
    "km": ["kilometrage_max", "kilometrage_min"], "annee": ["annee_min", "annee_max"],
    "categorie": ["categorie"], "type": ["categorie"], "boite": ["boite"], "transmission": ["boite"],
}

NUM_RE = re.compile(
    r"(?<![\w.,])(\d{1,3}(?:[ .]\d{3})+|\d+(?:[.,]\d+)?)"
    r"(\s*(?:k\b|mille\b))?"
    r"(\s*(?:kms?\b|kilometres?\b|kilometrage\b|dt\b|tnd\b|dinars?\b|d\b))?")
# Comparateurs. STRICTS (borne exclue) : « moins de », « inférieur à », « sous », « en dessous de », « < »,
# « plus de », « supérieur à », « au-dessus de », « > ». INCLUSIFS : « maximum », « jusqu'à », « au plus »,
# « pas plus de », « budget », « inférieur ou égal à », « <= », « au moins », « minimum », « à partir de », « >= ».
LT_RE = re.compile(r"(moins de|moins que|moins chere?s? que|inferieure?s? a|\bsous\b|en dessous de|<(?!=))")
MAX_RE = re.compile(r"(maximum|\bmax\b|au plus|jusqu' ?a|jusque|ne depass\w* pas|depassant pas|"
                    r"inferieure?s? ou egale?s? a|pas plus de|budget|<=|limite)")
GT_RE = re.compile(r"(plus de|plus que|superieure?s? a|au dessus de|>(?!=))")
MIN_RE = re.compile(r"(au moins|minimum|\bmin\b|superieure?s? ou egale?s? a|a partir de|>=|pas moins de)")
# À égalité de position, le DERNIER comparateur de la liste l'emporte : « pas plus de » (max) bat « plus de » (gt),
# « pas moins de » (min) bat « moins de » (lt).
COMPARATORS = {"gt": GT_RE, "lt": LT_RE, "min": MIN_RE, "max": MAX_RE}
# « entre 30 000 et 40 000 DT » : intervalle inclusif de prix ou de kilométrage.
RANGE_RE = re.compile(r"\bentre\s+(\d{1,3}(?:[ .]\d{3})+|\d+)\s*(k\b)?\s*(?:dt|tnd|dinars?)?\s+et\s+"
                      r"(\d{1,3}(?:[ .]\d{3})+|\d+)\s*(k\b)?\s*(dt|tnd|dinars?|kms?|kilometres?)\b")
PRICE_KW_RE = re.compile(r"(budget|prix|payer|cout\w*|tarif|dinars?|\bdt\b|tnd)")
KM_KW_RE = re.compile(r"(kilometrage|kilometres?|\bkms?\b|roule|compteur)")
YEAR_MIN_RE = re.compile(r"(apres|depuis|a partir de|des|posterieure?s? a|plus recente?s? que)\s*$")
YEAR_MAX_RE = re.compile(r"(avant|anterieure?s? a|jusqu' ?a|jusqu'en|au plus tard)\s*$")
AMOUNT_BEFORE_RE = re.compile(r"(moins|plus|max\w*|min\w*|budget|prix|kilometrage)\s*(de\s+|que\s+)?$")
ARTICLE_RE = re.compile(r"(?:^|\s)(une?|la|le|les|des|cette|ma)\s+$")


@dataclass
class Vocabulary:
    brands: dict[str, str]                 # nom normalisé -> marque
    models: list[tuple[str, str, str]]     # (nom normalisé, marque, modèle), du plus long au plus court
    cities: dict[str, str]                 # nom normalisé -> ville

    @classmethod
    def from_cars(cls, cars: list[dict]) -> Vocabulary:
        # Les annonces mal formées (non-objet, marque/modèle/ville absents) sont ignorées au lieu de planter.
        cars = [c for c in cars if isinstance(c, dict)
                and all(isinstance(c.get(k), str) and c[k] for k in ("marque", "modele", "ville"))]
        brands = {normalize(c["marque"]): c["marque"] for c in cars}
        for alias, brand in BRAND_ALIASES.items():
            if normalize(brand) in brands:
                brands[normalize(alias)] = brand
        models = sorted({(normalize(c["modele"]), c["marque"], c["modele"]) for c in cars},
                        key=lambda t: -len(t[0]))
        cities = {normalize(c["ville"]): c["ville"] for c in cars}
        return cls(brands, models, cities)

    def models_of(self, brand: str) -> set[str]:
        return {m for _, b, m in self.models if b == brand}


@dataclass
class ParseResult:
    criteria: dict = field(default_factory=dict)
    removed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reset: bool = False
    new_search: bool = False
    follow_up: bool = False
    help: bool = False
    unsupported: str | None = None
    car_word: bool = False
    vague: bool = False
    removed_values: dict = field(default_factory=dict)  # valeurs à retirer (« enlève diesel »)
    sort: str | None = None                            # ordre demandé (« les moins chères »)

    @property
    def recognized_count(self) -> int:
        return len(describe_criteria(self.criteria))


# ---------------------------------------------------------------- analyse

def parse_message(message: str, vocab: Vocabulary) -> ParseResult:
    text = message or ""
    norm = normalize(text)
    work = list(norm)  # copie que l'on « masque » au fur et à mesure
    r = ParseResult()

    def mask(start: int, end: int) -> None:
        for i in range(start, end):
            work[i] = " "

    def current() -> str:
        return "".join(work)

    def orig(m: re.Match) -> str:
        return text[m.start():m.end()].strip()

    # --- intentions générales
    r.reset = bool(RESET_RE.search(norm))
    r.help = bool(HELP_RE.search(norm))
    r.follow_up = bool(FOLLOW_RE.search(norm))
    r.new_search = bool(SEARCH_RE.search(norm))
    r.car_word = bool(CAR_WORD_RE.search(norm))
    m = UNSUPPORTED_RE.search(norm)
    if m:
        r.unsupported = orig(m)
    for m in RESET_RE.finditer(norm):
        mask(m.start(), m.end())

    # --- suppression de la seule borne basse (« sans prix minimum »)
    for m in REMOVAL_MIN_RE.finditer(current()):
        word = m.group(1) or m.group(2)
        key = "kilometrage_min" if word in ("kilometrage", "km") else "prix_min"
        if key not in r.removed:
            r.removed.append(key)
        mask(m.start(), m.end())

    # --- suppressions de critères (« peu importe la ville »)
    for m in REMOVAL_RE.finditer(current()):
        word = m.group(2).rstrip("s")
        for key in REMOVAL_KEYS.get(word, []):
            if key not in r.removed:
                r.removed.append(key)
        mask(m.start(), m.end())

    # --- intervalle d'années « entre 2018 et 2021 »
    for m in re.finditer(r"\bentre\s+(19\d{2}|20\d{2})\s+et\s+(19\d{2}|20\d{2})\b", current()):
        a, b = sorted((int(m.group(1)), int(m.group(2))))
        r.criteria["annee_min"], r.criteria["annee_max"] = a, b
        mask(m.start(), m.end())

    # --- intervalle de prix ou de kilométrage « entre 30 000 et 40 000 DT » (bornes incluses)
    for m in RANGE_RE.finditer(current()):
        lo, hi = sorted((_to_int(m.group(1), m.group(2)), _to_int(m.group(3), m.group(4))))
        prefix = "kilometrage" if m.group(5).startswith("k") else "prix"
        r.criteria[f"{prefix}_min"], r.criteria[f"{prefix}_max"] = lo, hi
        mask(m.start(), m.end())

    # --- modèles (avant les nombres : « 208 », « Série 3 », « 2008 »)
    brand_pos: dict[str, int] = {}
    for b_norm, brand in vocab.brands.items():
        mo = re.search(_word_pattern(b_norm), norm)
        if mo:
            brand_pos[brand] = min(brand_pos.get(brand, len(norm)), mo.start())
    found_models: list[tuple[str, str]] = []
    for model_norm, brand, model in vocab.models:
        for m in re.finditer(_word_pattern(model_norm), current()):
            if model_norm.isdigit():
                # Un modèle purement numérique n'est reconnu que juste après sa marque
                # ou un article (« Peugeot 2008 », « une 208 ») — sinon c'est un nombre.
                before = current()[:m.start()]
                brand_before = re.search(_word_pattern(brand) + r"\s+$", norm[:m.start()])
                if not brand_before and not ARTICLE_RE.search(before):
                    continue
            found_models.append((brand, model))
            mask(m.start(), m.end())

    # --- marques
    brands = sorted(brand_pos, key=brand_pos.get)  # ordre d'apparition (« Peugeot ou Renault »)
    if len(brands) > 1:
        r.criteria["marque"] = brands
    elif brands:
        r.criteria["marque"] = brands[0]

    # --- marques absentes de la base
    for other in OTHER_BRANDS:
        mo = re.search(_word_pattern(other), norm)
        if mo and normalize(other) not in vocab.brands:
            r.warnings.append(f"La marque « {orig(mo)} » n'est pas présente dans la base : critère ignoré.")
            mask(mo.start(), mo.end())

    # --- cohérence marque / modèle
    unique_models = sorted(set(found_models))
    if len(unique_models) > 1:
        r.warnings.append("Plusieurs modèles détectés (" + ", ".join(f"{b} {m}" for b, m in unique_models)
                          + ") : précisez un seul modèle.")
    elif unique_models:
        brand, model = unique_models[0]
        if isinstance(r.criteria.get("marque"), list):
            r.warnings.append(f"Avec plusieurs marques, je ne filtre pas sur le modèle « {model} ».")
        elif r.criteria.get("marque") and r.criteria["marque"] != brand:
            r.warnings.append(f"« {model} » est un modèle {brand}, pas {r.criteria['marque']} : "
                              "le modèle est ignoré.")
        elif len(brands) <= 1:
            r.criteria["marque"] = brand
            r.criteria["modele"] = model

    # --- modèle connu du référentiel mais absent des annonces chargées
    known = {(b, m) for _, b, m in vocab.models}
    for brand, (_, _, models) in BRANDS.items():
        for model in models:
            if (brand, model) in known or model.isdigit():
                continue
            mo = re.search(_word_pattern(model), current())
            if mo:
                r.warnings.append(f"Aucune annonce {brand} {model} n'est disponible dans la base : "
                                  "critère modèle ignoré.")
                mask(mo.start(), mo.end())
                if "marque" not in r.criteria and normalize(brand) in vocab.brands and len(brands) <= 1:
                    r.criteria["marque"] = brand

    # --- modèle inconnu juste après une marque (« Peugeot 3008 »)
    for b_norm, brand in vocab.brands.items():
        for m in re.finditer(_word_pattern(b_norm) + r"\s+([a-z]*\d[a-z0-9]*)\b(?!\s*(k\b|mille|km|dt|d\b|dinar|tnd))",
                             current()):
            token = m.group(1)
            year_like = token.isdigit() and re.fullmatch(r"(19[89]\d|20[0-3]\d)", token)
            if year_like or (token.isdigit() and len(token) >= 5):
                continue
            r.warnings.append(f"Je n'ai pas trouvé le modèle « {token} » pour {brand} dans la base : "
                              "critère ignoré.")
            mask(m.start(1), m.end(1))

    # --- villes
    city_hits = []
    for c_norm, city in vocab.cities.items():
        mo = re.search(_word_pattern(c_norm), current())
        if mo:
            city_hits.append((mo.start(), city))
            mask(mo.start(), mo.end())
    city_hits.sort()
    if len(city_hits) > 1:
        r.criteria["ville"] = [c for _, c in city_hits]
    elif city_hits:
        r.criteria["ville"] = city_hits[0][1]
    for other in OTHER_CITIES:
        mo = re.search(_word_pattern(other), current())
        if mo and normalize(other) not in vocab.cities:
            r.warnings.append(f"Aucune annonce n'est disponible à « {orig(mo)} » dans la base : critère ignoré.")
            mask(mo.start(), mo.end())
    known_words = set(vocab.brands) | set(vocab.cities) | {mn for mn, _, _ in vocab.models}
    for mo in re.finditer(r"(?:(?<=\s)|^)(?:à|À|sur|Sur|dans|vers)\s+([A-ZÉÈÀ][\wéèêàâîïôûç']+)", text):
        word = normalize(mo.group(1))
        if word not in known_words and not any(normalize(o) == word for o in OTHER_CITIES + OTHER_BRANDS):
            r.warnings.append(f"Je ne connais pas la ville « {mo.group(1)} » : critère ignoré. "
                              f"Villes disponibles : {', '.join(sorted(vocab.cities.values()))}.")

    # --- carburant, catégorie, boîte
    # --- préférences d'ordre (« les moins chères », « plus récentes ») : retirées avant le reste
    sort_hits = []
    for option, pat in SORT_PATTERNS.items():
        for mo in re.finditer(pat, current()):
            sort_hits.append((mo.start(), option))
            mask(mo.start(), mo.end())
    if sort_hits:
        r.sort = min(sort_hits)[1]

    # --- carburant, catégorie, boîte (plusieurs valeurs possibles : « diesel ou hybride »)
    for key, patterns in (("carburant", FUEL_PATTERNS), ("categorie", CATEGORY_PATTERNS),
                          ("boite", TRANSMISSION_PATTERNS)):
        hits = sorted((mo.start(), value) for value, pat in patterns.items()
                      for mo in [re.search(pat, current())] if mo)
        for pat in patterns.values():
            for mo in re.finditer(pat, current()):
                mask(mo.start(), mo.end())
        if len(hits) > 1:
            r.criteria[key] = [v for _, v in hits]
        elif hits:
            r.criteria[key] = hits[0][1]

    # --- nombres : prix, kilométrage, années
    _parse_numbers(current(), text, r)

    # --- termes vagues ou non gérés
    for pattern, key, msg in VAGUE_TERMS:
        mo = re.search(pattern, norm)
        if mo and (key is None or key not in r.criteria):
            r.warnings.append(msg.format(m=text[mo.start():mo.end()]))
            r.vague = True

    # --- « enlève le critère diesel » : les valeurs citées deviennent des retraits
    if REMOVE_VALUE_RE.search(norm):
        for key in TEXT_KEYS:
            if key in r.criteria:
                r.removed_values[key] = r.criteria.pop(key)
    return r


def _nearest(regexes: dict[str, re.Pattern], before: str) -> str | None:
    best, best_end = None, -1
    for name, rx in regexes.items():
        for m in rx.finditer(before):
            if m.end() > best_end or (m.end() == best_end and best and len(m.group(0)) > 3):
                best, best_end = name, m.end()
    return best


def _to_int(digits: str, k_suffix: str | None = None) -> int:
    """« 40 000 », « 40.000 », « 40000 », « 40,5 » (+ suffixe « k » / « mille ») -> entier."""
    if re.fullmatch(r"\d{1,3}(?:[ .]\d{3})+", digits):
        value = float(re.sub(r"[ .]", "", digits))
    else:
        value = float(digits.replace(",", "."))
    if k_suffix:
        value *= 1000
    return int(round(value))


def _parse_numbers(work: str, text: str, r: ParseResult) -> None:
    prev_end = 0
    exact_years: list[int] = []
    for m in NUM_RE.finditer(work):
        digits, k_suffix, unit = m.group(1), m.group(2), (m.group(3) or "").strip()
        raw = text[m.start():m.end()].strip()
        before = work[max(prev_end, m.start() - 40):m.start()]
        prev_end = m.end()
        value = _to_int(digits, k_suffix)
        # « -5000 DT » : le signe moins est neutralisé par normalize() ; on le relit dans le texte d'origine.
        # (« 2015-2018 » n'est pas concerné : le tiret y suit directement un chiffre.)
        negative = (m.start() >= 1 and text[m.start() - 1] in "-−"
                    and (m.start() == 1 or not text[m.start() - 2].isalnum()))

        if unit.startswith("k"):
            kind = "km"
        elif unit:
            kind = "price"
        elif not k_suffix and re.fullmatch(r"(19[89]\d|20[0-3]\d)", digits) and not AMOUNT_BEFORE_RE.search(before):
            kind = "year"
        else:
            kind = _nearest({"price": PRICE_KW_RE, "km": KM_KW_RE}, before)
            if kind is None:
                kind = "amount" if any(rx.search(before) for rx in COMPARATORS.values()) else "unknown"

        if kind == "year":
            if YEAR_MIN_RE.search(before):
                after = re.search(r"apres\s*$", before)
                r.criteria["annee_min"] = value + 1 if after else value
            elif YEAR_MAX_RE.search(before):
                strict = re.search(r"avant\s*$", before)
                r.criteria["annee_max"] = value - 1 if strict else value
            else:
                exact_years.append(value)
            continue

        if kind == "unknown":
            if value >= 1000:
                r.warnings.append(f"Je ne sais pas si « {raw} » est un prix ou un kilométrage. "
                                  "Précisez « DT » ou « km ».")
            continue

        if negative:
            what = "kilométrage" if kind == "km" else "prix"
            r.warnings.append(f"« -{raw} » : un {what} ne peut pas être négatif, critère ignoré.")
            continue

        comparator = _nearest(COMPARATORS, before) or "max"   # « budget 40000 », « 40000 DT » : maximum
        side = "min" if comparator in ("min", "gt") else "max"
        strict = comparator in ("lt", "gt")

        if kind == "amount":
            if f"prix_{side}" not in r.criteria:
                kind = "price"
            else:
                r.warnings.append(f"Je ne sais pas si « {raw} » est un prix ou un kilométrage. "
                                  "Précisez « DT » ou « km ».")
                continue

        key = f"prix_{side}" if kind == "price" else f"kilometrage_{side}"
        if value < 1000:
            hint = format_price(value * 1000) if kind == "price" else format_km(value * 1000)
            r.warnings.append(f"« {raw} » semble trop faible pour un "
                              f"{'prix' if kind == 'price' else 'kilométrage'} de voiture : critère ignoré. "
                              f"Vouliez-vous dire {hint} ?")
            continue
        if key in r.criteria and r.criteria[key] != value:
            r.warnings.append(f"Deux valeurs pour {CRITERIA_LABELS[key].lower()} : je garde "
                              f"{format_value(key, r.criteria[key])} et j'ignore « {raw} ».")
            continue
        r.criteria[key] = value
        if strict:
            r.criteria[key + STRICT_SUFFIX] = True

    if exact_years:
        if len(set(exact_years)) > 1:
            r.warnings.append("Plusieurs années détectées (" + ", ".join(map(str, exact_years))
                              + ") : indiquez une année ou un intervalle (ex. entre 2018 et 2021).")
        elif not any(k in r.criteria for k in YEAR_KEYS):
            r.criteria["annee_min"] = r.criteria["annee_max"] = exact_years[0]


# ---------------------------------------------------------------- dialogue

INTENT_LABELS = {
    "search": "Recherche",
    "follow_up": "Suivi",
    "sort": "Tri",
    "reset": "Réinitialisation",
    "no_criteria": "Sans critère",
    "ambiguous": "Ambigu",
    "unsupported": "Hors périmètre",
    "help": "Aide",
}

SORT_RESPONSES = {
    "Prix croissant": "Voici les voitures les moins chères correspondant à vos critères.",
    "Prix décroissant": "Voici les voitures les plus chères correspondant à vos critères.",
    "Année la plus récente": "Voici les modèles les plus récents correspondant à vos critères.",
    "Kilométrage croissant": "Voici les voitures les moins kilométrées correspondant à vos critères.",
}
EMPTY_RESPONSE = ("Je n'ai trouvé aucune voiture correspondant exactement à ces critères. "
                  "On peut essayer d'élargir la recherche.")


@dataclass
class Turn:
    message: str
    intent: str
    criteria: dict                       # critères actifs après ce message
    extracted: dict                      # critères lus dans ce message
    added: dict = field(default_factory=dict)
    changed: dict = field(default_factory=dict)   # clé -> (ancien, nouveau)
    removed: dict = field(default_factory=dict)   # clé -> ancienne valeur
    warnings: list[str] = field(default_factory=list)
    explanation: str = ""
    response: str = ""
    result_count: int | None = None
    replaced_previous: bool = False
    sort: str | None = None              # ordre demandé dans ce message (None = inchangé)

    @property
    def recognized_count(self) -> int:
        return len(describe_criteria(self.extracted))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["recognized_count"] = self.recognized_count
        return d


# ---------------------------------------------------------------- phrases naturelles

def _agree(word: str, plural: bool) -> str:
    """Accord des adjectifs : diesel et essence sont invariables."""
    if plural and word not in ("diesel", "essence") and not word.endswith("s"):
        return word + "s"
    return word


def natural_description(criteria: dict, n: int) -> str:
    """« voitures Peugeot diesel automatiques à Sfax jusqu'à 40 000 DT »."""
    plural = n != 1
    cat = criteria.get("categorie")
    if isinstance(cat, str):
        noun = cat if cat == "SUV" else _agree(cat.lower(), plural)
    else:
        noun = _agree("voiture", plural)
    parts = [noun]
    brand, model = criteria.get("marque"), criteria.get("modele")
    if brand:
        parts.append(format_value("marque", brand) + (f" {model}" if model else ""))
    for key in ("carburant", "boite"):
        value = criteria.get(key)
        if isinstance(value, list):
            parts.append(" ou ".join(v.lower() for v in value))
        elif value:
            parts.append(_agree(value.lower(), plural))
    if isinstance(cat, list):
        parts.append("(" + " ou ".join(cat) + ")")
    if criteria.get("ville"):
        parts.append("à " + format_value("ville", criteria["ville"]))
    if criteria.get("prix_min"):
        parts.append(("à plus de " if criteria.get("prix_min_strict") else "à partir de ")
                     + format_price(criteria["prix_min"]))
    if criteria.get("prix_max"):
        parts.append(("à moins de " if criteria.get("prix_max_strict") else "jusqu'à ")
                     + format_price(criteria["prix_max"]))
    if criteria.get("kilometrage_min"):
        parts.append(f"avec {'plus de ' if criteria.get('kilometrage_min_strict') else 'au moins '}"
                     f"{format_km(criteria['kilometrage_min'])}")
    if criteria.get("kilometrage_max"):
        link = "et" if criteria.get("kilometrage_min") else "avec"
        if criteria.get("kilometrage_max_strict"):
            parts.append(f"{link} moins de {format_km(criteria['kilometrage_max'])}")
        else:
            parts.append(f"{link} {format_km(criteria['kilometrage_max'])} maximum")
    lo, hi = criteria.get("annee_min"), criteria.get("annee_max")
    if lo and hi:
        parts.append(f"de {lo}" if lo == hi else f"de {lo} à {hi}")
    elif lo:
        parts.append(f"depuis {lo}")
    elif hi:
        parts.append(f"jusqu'à {hi}")
    return " ".join(parts)


def _diff(before: dict, after: dict) -> tuple[dict, dict, dict]:
    # Les indicateurs internes « _strict » accompagnent leur borne : ils ne sont pas des critères à part.
    before = {k: v for k, v in before.items() if not k.endswith(STRICT_SUFFIX)}
    after = {k: v for k, v in after.items() if not k.endswith(STRICT_SUFFIX)}
    added = {k: v for k, v in after.items() if k not in before}
    changed = {k: (before[k], v) for k, v in after.items() if k in before and before[k] != v}
    removed = {k: v for k, v in before.items() if k not in after}
    return added, changed, removed


def _changes_sentence(added: dict, changed: dict, removed: dict) -> str:
    # Cas fréquent formulé plus naturellement : seul le budget change.
    if set(added) | set(changed) == {"prix_max"} and not removed:
        if "prix_max" in added:
            return f"D'accord, je limite la recherche à {format_price(added['prix_max'])}."
        old, new = changed["prix_max"]
        return f"D'accord, je passe le budget de {format_price(old)} à {format_price(new)}."
    parts = []
    if added:
        parts.append("j'ajoute " + ", ".join(f"{label} = {v}" for label, v in describe_criteria(added)))
    for k, (old, new) in changed.items():
        if k in YEAR_KEYS:
            continue
        parts.append(f"je remplace {CRITERIA_LABELS[k]} : {format_value(k, old)} → {format_value(k, new)}")
    if any(k in YEAR_KEYS for k in changed):
        parts.append("je mets à jour l'année")
    if removed:
        labels = {CRITERIA_LABELS[k].replace(" minimum", "").replace(" maximum", "") if k in YEAR_KEYS
                  else CRITERIA_LABELS[k] for k in removed}
        parts.append("je retire " + ", ".join(sorted(labels)))
    if not parts:
        return ""
    if added and not (changed or removed):
        return f"Bien sûr, {parts[0]} à votre recherche précédente."
    return "Bien sûr : " + " ; ".join(parts) + "."


def _results_sentence(criteria: dict, n: int, follow_up: bool = False) -> str:
    if n == 0:
        return EMPTY_RESPONSE
    verb = "J'ai maintenant" if follow_up else "J'ai trouvé"
    return f"{verb} {n} {natural_description(criteria, n)}."


def _remove_values(base: dict, removed_values: dict, notes: list[str]) -> None:
    """Retire des valeurs précises (« enlève diesel ») d'un critère éventuellement multiple."""
    for key, value in removed_values.items():
        wanted = {normalize(v) for v in (value if isinstance(value, list) else [value])}
        current = base.get(key)
        values = current if isinstance(current, list) else ([current] if current is not None else [])
        remaining = [v for v in values if normalize(v) not in wanted]
        if len(remaining) == len(values):
            notes.append(f"{CRITERIA_LABELS[key]} « {format_value(key, value)} » n'était pas un critère actif.")
        elif not remaining:
            base.pop(key)
            if key == "marque":
                base.pop("modele", None)
        else:
            base[key] = remaining if len(remaining) > 1 else remaining[0]


# ---------------------------------------------------------------- traitement d'un message

def _without_criteria(t: Turn, p: ParseResult, prev: dict, cars: list[dict], message: str) -> Turn:
    """Message sans nouveau critère : tri, réinitialisation, aide, ambiguïté…"""
    if p.reset:
        t.intent, t.criteria, t.removed, t.sort = "reset", {}, prev, p.sort
        t.response = "C'est noté, j'ai effacé tous les critères. Que recherchez-vous maintenant ?"
        t.explanation = "Réinitialisation demandée : aucun critère conservé."
        t.result_count = len(cars)
    elif p.sort:
        # « les moins chères », « plus récentes » : on garde les critères et on change l'ordre.
        t.intent, t.sort = "sort", p.sort
        t.result_count = n = len(filter_cars(cars, prev))
        t.response = SORT_RESPONSES[p.sort] if n else EMPTY_RESPONSE
        if p.sort == "Prix croissant" and "prix_max" not in prev and n:
            t.response += " Pour fixer un budget, précisez un montant, par exemple « moins de 40 000 DT »."
        t.explanation = f"Ordre demandé : {p.sort}. Critères inchangés."
    elif p.help and not p.vague:
        t.intent = "help"
        hello = "Avec plaisir !" if "merci" in normalize(message) else "Bonjour !"
        t.response = (f"{hello} Décrivez la voiture recherchée : marque, modèle, ville, carburant, boîte, "
                      "budget, kilométrage ou année. Je garde vos critères d'un message à l'autre "
                      "(« à Tunis seulement », « augmente le budget à 50 000 DT ») ; écrivez « nouvelle "
                      "recherche » pour repartir de zéro.")
    elif p.warnings or p.vague:
        t.intent = "ambiguous"
        t.response = ("Je n'ai pas pu transformer votre demande en critère précis"
                      + (" ; vos critères actuels restent inchangés." if prev else "."))
        t.explanation = "Aucun critère exploitable : rien n'a été modifié."
    elif p.car_word or p.new_search:
        t.intent = "no_criteria"
        t.result_count = len(filter_cars(cars, prev))
        if prev:
            t.response = ("Je n'ai pas identifié de nouveau critère : voici les résultats de votre recherche "
                          "en cours. Écrivez « nouvelle recherche » pour repartir de zéro.")
        else:
            t.response = ("Je n'ai pas identifié de filtre précis. Je vous affiche toutes les annonces "
                          f"disponibles ({len(cars)}).")
        t.explanation = "Aucun nouveau critère reconnu."
    else:
        t.intent = "unsupported"
        t.response = ("Je n'ai pas compris votre demande. Je peux rechercher des voitures par marque, "
                      "modèle, ville, carburant, budget, kilométrage ou année. "
                      "Exemple : diesel à Tunis moins de 40 000 DT.")
    return t


def process_message(message: str, previous: dict | None, cars: list[dict],
                    vocab: Vocabulary | None = None) -> Turn:
    """Interprète un message dans le contexte des critères précédents.

    Règle de contexte : les critères précédents sont CONSERVÉS par défaut ; un message
    ajoute, remplace ou retire des critères. Seule une demande explicite
    (« nouvelle recherche », « réinitialiser »…) repart de zéro.
    """
    vocab = vocab or Vocabulary.from_cars(cars)
    prev = dict(previous or {})
    p = parse_message(message, vocab)
    t = Turn(message=message, intent="search", criteria=prev, extracted=dict(p.criteria),
             warnings=list(p.warnings))

    if not (message or "").strip():
        t.intent, t.response = "no_criteria", "Écrivez votre recherche, par exemple : Peugeot diesel à Tunis."
        return t
    if p.unsupported:
        t.intent, t.extracted = "unsupported", {}
        t.response = (f"Je suis spécialisé dans la recherche d'annonces de voitures à vendre ; je ne peux pas "
                      f"traiter « {p.unsupported} ». Vos critères actuels restent inchangés. "
                      "Essayez par exemple : Peugeot diesel à Tunis moins de 40 000 DT.")
        return t
    if not p.criteria and not p.removed and not p.removed_values:
        return _without_criteria(t, p, prev, cars, message)

    # --- recherche (sans contexte ou après réinitialisation) ou suivi (contexte conservé)
    follow_up = bool(prev) and not p.reset
    base = dict(prev) if follow_up else {}
    t.replaced_previous = p.reset and bool(prev)

    notes: list[str] = []
    for key in p.removed:
        base.pop(key, None)
    _remove_values(base, p.removed_values, notes)
    if any(k in p.criteria for k in YEAR_KEYS):
        for k in YEAR_KEYS:
            base.pop(k, None)
    new_brand = p.criteria.get("marque")
    if new_brand and base.get("modele") and "modele" not in p.criteria and base.get("marque") != new_brand:
        notes.append(f"Le modèle {base['modele']} ne correspond pas à {format_value('marque', new_brand)} : "
                     "je le retire.")
        base.pop("modele")
    for key in BOUND_KEYS:  # une nouvelle borne remplace aussi son caractère strict/inclusif
        if key in p.criteria:
            base.pop(key + STRICT_SUFFIX, None)
    base.update(p.criteria)
    for key in BOUND_KEYS:  # borne retirée => indicateur retiré
        if key not in base:
            base.pop(key + STRICT_SUFFIX, None)
    for lo, hi, what in (("prix_min", "prix_max", "prix"), ("kilometrage_min", "kilometrage_max", "kilométrage")):
        if base.get(lo) is not None and base.get(hi) is not None and (
                base[lo] > base[hi] or (base[lo] == base[hi] and (base.get(lo + STRICT_SUFFIX)
                                                                   or base.get(hi + STRICT_SUFFIX)))):
            t.warnings.append(f"Critères contradictoires : {what} minimum {bound_text(lo, base)} et {what} "
                              f"maximum {bound_text(hi, base)}. Aucune voiture ne peut correspondre ; "
                              "corrigez l'une des deux bornes.")
    t.criteria, t.intent, t.sort = base, ("follow_up" if follow_up else "search"), p.sort

    t.added, t.changed, t.removed = _diff(prev if follow_up else {}, base)
    n = t.result_count = len(filter_cars(cars, base))

    described = ", ".join(f"{label} = {v}" for label, v in describe_criteria(base)) or "aucun critère"
    if follow_up:
        head = (_changes_sentence(t.added, t.changed, t.removed)
                or "Ces critères étaient déjà actifs : votre recherche reste inchangée.")
        t.explanation = f"Suivi de la recherche précédente. Critères actifs : {described}."
    else:
        if t.replaced_previous:
            head = "Nouvelle recherche : j'ai effacé vos critères précédents."
        else:
            head = "Parfait ! J'ai compris votre recherche." if n else "J'ai bien compris votre recherche."
        t.explanation = f"Nouvelle recherche. Critères : {described}."
    tail = [SORT_RESPONSES[p.sort].replace("Voici", "Je vous montre d'abord")] if p.sort and n else []
    t.response = " ".join([head, *notes, _results_sentence(base, n, follow_up), *tail])
    return t
