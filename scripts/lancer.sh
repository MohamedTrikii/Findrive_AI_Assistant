#!/usr/bin/env bash
# ==========================================================
#  AutoMind AI - lancement du projet (macOS / Linux)
#     ./scripts/lancer.sh          lance l'application
#     ./scripts/lancer.sh tests    exécute les tests automatisés
# ==========================================================
set -e
cd "$(dirname "$0")/.."

echo
echo "  AutoMind AI - Assistant de recherche automobile"
echo "  ------------------------------------------------"
echo

# 1. Trouver Python
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "[ERREUR] Python est introuvable. Installez Python 3.10 ou plus récent."
  exit 1
fi
echo "[OK] $($PY --version 2>&1)"

# 2. Installer les dépendances si nécessaire
if ! $PY -c "import streamlit, pytest" >/dev/null 2>&1; then
  echo "[..] Installation des dépendances (streamlit, pytest)..."
  $PY -m pip install -r requirements-dev.txt
fi
echo "[OK] Dépendances présentes"

# 3. Générer la base si elle est absente
if [ ! -f data/cars.json ]; then
  echo "[..] Génération de cars.json (200 annonces, graine 42)..."
  $PY -m automind.generate_cars --count 200 --seed 42
fi
echo "[OK] Base de données data/cars.json"

# 4. Tests ou application
if [ "${1:-}" = "tests" ]; then
  echo
  echo "[..] Exécution des tests..."
  exec $PY -m pytest -v
fi

echo
echo "[..] Ouverture de l'application sur http://localhost:8501 (Ctrl+C pour arrêter)"
echo
exec $PY -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
