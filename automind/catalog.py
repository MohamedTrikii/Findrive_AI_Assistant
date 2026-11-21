"""Référentiel de données AutoMind AI.

Source unique pour les marques, modèles, villes, carburants, catégories,
boîtes et états. Utilisé par le générateur, la validation et (indirectement,
via les données) le chatbot.

Toutes les valeurs de prix sont FICTIVES : ce ne sont pas des cotes du marché.
"""

from __future__ import annotations

ESSENCE = "Essence"
DIESEL = "Diesel"
HYBRIDE = "Hybride"
ELECTRIQUE = "Électrique"

FUELS = [ESSENCE, DIESEL, HYBRIDE, ELECTRIQUE]
CATEGORIES = ["Citadine", "Compacte", "Berline", "SUV"]
TRANSMISSIONS = ["Manuelle", "Automatique"]
CONDITIONS = ["Excellent", "Très bon", "Bon", "Correct"]

# Villes tunisiennes et poids de tirage (part approximative des annonces).
CITIES = {
    "Tunis": 0.22,
    "Ariana": 0.10,
    "Sfax": 0.14,
    "Sousse": 0.13,
    "Monastir": 0.08,
    "Nabeul": 0.08,
    "Bizerte": 0.07,
    "Gabès": 0.06,
    "Mahdia": 0.06,
    "Kairouan": 0.06,
}

# Marque -> (poids de tirage, premium ?, {modèle: (catégorie, prix neuf fictif DT, carburants possibles)})
BRANDS: dict[str, tuple[float, bool, dict[str, tuple[str, int, list[str]]]]] = {
    "Peugeot": (0.13, False, {
        "208": ("Citadine", 62000, [ESSENCE, DIESEL, ELECTRIQUE]),
        "301": ("Berline", 58000, [ESSENCE, DIESEL]),
        "308": ("Compacte", 82000, [ESSENCE, DIESEL, HYBRIDE]),
        "2008": ("SUV", 88000, [ESSENCE, DIESEL, ELECTRIQUE]),
    }),
    "Renault": (0.11, False, {
        "Clio": ("Citadine", 58000, [ESSENCE, DIESEL]),
        "Megane": ("Compacte", 78000, [ESSENCE, DIESEL]),
        "Symbol": ("Berline", 50000, [ESSENCE, DIESEL]),
        "Captur": ("SUV", 80000, [ESSENCE, HYBRIDE]),
        "Zoe": ("Citadine", 85000, [ELECTRIQUE]),
    }),
    "Volkswagen": (0.09, False, {
        "Polo": ("Citadine", 68000, [ESSENCE, DIESEL]),
        "Golf": ("Compacte", 98000, [ESSENCE, DIESEL, HYBRIDE]),
        "Passat": ("Berline", 135000, [ESSENCE, DIESEL]),
        "Tiguan": ("SUV", 150000, [ESSENCE, DIESEL]),
    }),
    "Toyota": (0.07, False, {
        "Yaris": ("Citadine", 66000, [ESSENCE, HYBRIDE]),
        "Corolla": ("Berline", 90000, [ESSENCE, HYBRIDE]),
        "C-HR": ("SUV", 110000, [HYBRIDE]),
        "RAV4": ("SUV", 145000, [ESSENCE, HYBRIDE]),
    }),
    "Hyundai": (0.09, False, {
        "i10": ("Citadine", 42000, [ESSENCE]),
        "i20": ("Citadine", 55000, [ESSENCE]),
        "Accent": ("Berline", 56000, [ESSENCE, DIESEL]),
        "Tucson": ("SUV", 120000, [ESSENCE, DIESEL, HYBRIDE]),
        "Kona": ("SUV", 95000, [ESSENCE, HYBRIDE, ELECTRIQUE]),
    }),
    "Kia": (0.09, False, {
        "Picanto": ("Citadine", 45000, [ESSENCE]),
        "Rio": ("Citadine", 54000, [ESSENCE, DIESEL]),
        "Sportage": ("SUV", 125000, [ESSENCE, DIESEL, HYBRIDE]),
    }),
    "Citroën": (0.06, False, {
        "C3": ("Citadine", 55000, [ESSENCE, DIESEL]),
        "C4": ("Compacte", 80000, [ESSENCE, DIESEL, ELECTRIQUE]),
        "C-Elysée": ("Berline", 52000, [ESSENCE, DIESEL]),
    }),
    "Fiat": (0.05, False, {
        "Punto": ("Citadine", 45000, [ESSENCE, DIESEL]),
        "Panda": ("Citadine", 42000, [ESSENCE]),
        "Tipo": ("Compacte", 58000, [ESSENCE, DIESEL]),
    }),
    "Ford": (0.04, False, {
        "Fiesta": ("Citadine", 55000, [ESSENCE, DIESEL]),
        "Focus": ("Compacte", 75000, [ESSENCE, DIESEL]),
        "Kuga": ("SUV", 120000, [ESSENCE, DIESEL, HYBRIDE]),
    }),
    "Opel": (0.03, False, {
        "Corsa": ("Citadine", 56000, [ESSENCE, DIESEL, ELECTRIQUE]),
        "Astra": ("Compacte", 78000, [ESSENCE, DIESEL]),
    }),
    "Seat": (0.04, False, {
        "Ibiza": ("Citadine", 58000, [ESSENCE, DIESEL]),
        "Leon": ("Compacte", 80000, [ESSENCE, DIESEL]),
        "Arona": ("SUV", 78000, [ESSENCE]),
    }),
    "Skoda": (0.03, False, {
        "Fabia": ("Citadine", 55000, [ESSENCE]),
        "Octavia": ("Berline", 88000, [ESSENCE, DIESEL]),
        "Kodiaq": ("SUV", 130000, [ESSENCE, DIESEL]),
    }),
    "Nissan": (0.04, False, {
        "Micra": ("Citadine", 50000, [ESSENCE]),
        "Qashqai": ("SUV", 105000, [ESSENCE, DIESEL, HYBRIDE]),
        "Leaf": ("Compacte", 110000, [ELECTRIQUE]),
    }),
    "Dacia": (0.05, False, {
        "Logan": ("Berline", 42000, [ESSENCE, DIESEL]),
        "Sandero": ("Citadine", 40000, [ESSENCE, DIESEL]),
        "Duster": ("SUV", 62000, [ESSENCE, DIESEL]),
        "Spring": ("Citadine", 48000, [ELECTRIQUE]),
    }),
    "BMW": (0.03, True, {
        "Série 1": ("Compacte", 135000, [ESSENCE, DIESEL]),
        "Série 3": ("Berline", 190000, [ESSENCE, DIESEL, HYBRIDE]),
        "X1": ("SUV", 175000, [ESSENCE, DIESEL, HYBRIDE]),
    }),
    "Mercedes": (0.03, True, {
        "Classe A": ("Compacte", 145000, [ESSENCE, DIESEL]),
        "Classe C": ("Berline", 210000, [ESSENCE, DIESEL, HYBRIDE]),
        "GLA": ("SUV", 185000, [ESSENCE, DIESEL]),
    }),
    "Audi": (0.02, True, {
        "A3": ("Compacte", 140000, [ESSENCE, DIESEL]),
        "A4": ("Berline", 185000, [ESSENCE, DIESEL]),
        "Q3": ("SUV", 180000, [ESSENCE, DIESEL]),
    }),
}

PREMIUM_BRANDS = sorted(b for b, (_, premium, _) in BRANDS.items() if premium)

MIN_YEAR = 2012
REFERENCE_YEAR = 2026  # année de référence fixe => génération reproductible
MAX_YEAR = REFERENCE_YEAR - 1

REQUIRED_FIELDS = [
    "id", "marque", "modele", "annee", "ville", "carburant", "prix",
    "kilometrage", "boite", "categorie", "etat", "source",
]


def models_of(brand: str) -> dict[str, tuple[str, int, list[str]]]:
    return BRANDS[brand][2]
