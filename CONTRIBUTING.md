# Contribuer à Findrive Assistant

Merci de votre intérêt pour le projet ! Ce guide décrit comment installer l'environnement, proposer une modification et la faire accepter.

## Installer l'environnement

```bash
git clone https://github.com/MohamedTrikii/Findrive_AI_Assistant.git
cd Findrive_AI_Assistant
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
streamlit run app.py
```

## Workflow Git

1. Partir de `main` à jour et créer une branche dédiée :

   | Préfixe | Usage | Exemple |
   |---|---|---|
   | `feat/` | Nouvelle fonctionnalité | `feat/filtre-couleur` |
   | `fix/` | Correction de bug | `fix/borne-prix-inclusive` |
   | `docs/` | Documentation seule | `docs/guide-deploiement` |
   | `refactor/` | Restructuration sans changement de comportement | `refactor/moteur-intentions` |
   | `test/`, `ci/`, `chore/` | Tests, intégration continue, maintenance | `ci/cache-playwright` |

2. Faire des commits petits et cohérents (voir la convention ci-dessous).
3. Vérifier localement que tout passe (section suivante).
4. Ouvrir une Pull Request vers `main` en remplissant le modèle proposé. La CI doit être verte avant la fusion.

## Convention de commits

Les messages suivent [Conventional Commits](https://www.conventionalcommits.org/fr/v1.0.0/), rédigés en français, à l'impératif présent ou au présent :

```
<type>(<portée optionnelle>): <résumé court>

<corps optionnel : le pourquoi, pas le comment>
```

Types utilisés : `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `ci`, `chore`.
Exemples : `feat(chatbot): comprend « entre X et Y km »`, `fix(search): exclut la borne stricte du prix`.

## Avant d'ouvrir une Pull Request

```bash
ruff check .                                    # lint et tri des imports
pytest --cov                                    # suite principale
pytest qa/test_code --ignore=qa/test_code/ui    # campagne QA hors navigateur
```

- Toute nouvelle règle de compréhension du langage s'accompagne de tests dans `tests/test_chatbot.py`.
- Si vous modifiez la génération des données, régénérez-les (`python -m findrive.generate_cars`) et committez `data/cars.json` et `docs/data_summary.md` : la CI vérifie que le fichier est reproductible.
- Mettez à jour le [CHANGELOG](CHANGELOG.md) dans la section « Non publié ».

## Style de code

- Python 3.10+, annotations de type sur les fonctions publiques.
- Longueur de ligne et règles : voir `[tool.ruff]` dans `pyproject.toml`.
- Le moteur (`findrive/chatbot.py`, `findrive/search.py`) reste indépendant de Streamlit.
- Tout contenu dynamique inséré dans du HTML passe par `html.escape`.

## Signaler un bug ou proposer une idée

Utilisez les [modèles d'issue](https://github.com/MohamedTrikii/Findrive_AI_Assistant/issues/new/choose). Pour une faille de sécurité, suivez plutôt [SECURITY.md](SECURITY.md).
