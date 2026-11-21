# Notes de conception UI — AutoMind AI

## Intention

Faire comprendre dès le premier écran qu'il s'agit d'un **assistant conversationnel** de recherche automobile. L'utilisateur parle à l'assistant, l'assistant comprend, et **les voitures apparaissent dans la conversation**. Il n'y a ni page ni panneau de résultats séparé.

## Structure de la page (une seule colonne, 980 px max)

1. **Barre supérieure** : logo, « AutoMind AI », pastille verte « Assistant prêt », bouton « ＋ Nouvelle conversation ».
2. **Accueil** (conversation vide uniquement) : icône, titre « Votre prochaine voiture commence ici. », sous-titre, chiffres réels de la base, 4 cartes de suggestion en grille 2 × 2. Un clic envoie le message.
3. **Conversation** : messages de l'utilisateur à droite (bulle bleue, avatar à droite), réponses de l'assistant à gauche (avatar voiture, sans bulle, pour laisser la place aux cartes).
4. **Saisie fixée en bas** (`st.chat_input`) : multiligne, Entrée = envoyer, Maj + Entrée = nouvelle ligne, envoi vide impossible, ombre portée et anneau bleu au focus.
5. **Barre latérale repliée** : filtres manuels optionnels (leur résultat est publié dans le chat), historique, statistiques, fonctionnement. Elle n'encombre jamais l'écran principal.

## Anatomie d'une réponse de l'assistant

| Bloc | Rôle |
|---|---|
| Pastille d'intention (« Recherche », « Recherche mise à jour », « Nouvel ordre », « Précision nécessaire »…) | Dire en un mot ce que l'assistant a compris |
| Texte naturel | « D'accord, je limite la recherche à 40 000 DT. J'ai maintenant 3 voitures diesel à Sfax jusqu'à 40 000 DT. » |
| 🔎 Puces de recherche | « Diesel », « Sfax », « Budget ≤ 40 000 DT », « ≤ 120 000 km »… Sur la dernière réponse elles sont cliquables (✕ = retirer), sur les anciennes elles sont figées |
| Changements | + ajouté (vert), ⇄ modifié (bleu), ~~retiré~~ (barré), seulement lorsqu'une recherche est modifiée |
| Avertissements | Encadré orange pour ce qui n'est pas pris en compte |
| Synthèse | Fourchette de prix, moyenne, ordre appliqué |
| Carrousel de cartes | 6 cartes défilant horizontalement (au doigt sur mobile) + « Afficher plus » |
| Relance | « Voulez-vous que je privilégie le prix, le kilométrage ou l'année ? » avec 3 boutons |
| Pistes d'affinage | « Moins de 60 000 DT · 4 »… avec le nombre réel de résultats |

Les actions (relance, pistes, puces) ne sont proposées que sur la **dernière** réponse, pour éviter d'agir sur un contexte dépassé. Chaque clic envoie un **message visible** : aucune modification invisible des critères.

## Cartes véhicules

- **Image** : illustration SVG intégrée (silhouette selon la catégorie, teinte de carrosserie selon la référence, vitres, phare). Aucune ressource externe, donc pas de lien cassé et pas de besoin d'Internet.
- Marque et année sur l'image, repères « Meilleur prix » (vert), « Plus faible km », « Plus récente ».
- Nom, année · ville, **prix en bleu** bien visible.
- Pastilles carburant (couleur par énergie), boîte, catégorie ; ✓ sur ce qui correspond aux critères.
- Kilométrage, année, ville avec icônes ; bouton **« Voir les détails »**.

## Fiche détaillée

Affichée **comme un message de l'assistant**, dans le fil :
- grande illustration ;
- prix ;
- grille de 8 caractéristiques (année, km, carburant, boîte, catégorie, état, ville, référence) ;
- **comparaison avec les autres résultats de la recherche** (prix et kilométrage face à la moyenne, ancienneté) ;
- mention « données fictives ».

Le bouton « ↩ Fermer la fiche et revenir à la conversation » retire la fiche et la demande associée.

## États particuliers

- **Aucun résultat** : encadré pointillé ambré 🔍 et pistes cliquables (augmenter le budget, accepter plus de km, supprimer le carburant, étendre la zone). Seules les pistes qui donnent réellement des résultats sont proposées, avec leur nombre.
- **Aide, demande hors périmètre ou imprécise** : réponse textuelle et suggestions de départ.
- **Traitement** : trois points animés et « Je recherche les véhicules correspondants… ».

## Identité visuelle

| Élément | Choix |
|---|---|
| Couleurs | Marine `#0f1b2d` (titres), bleu `#2563eb` (action, prix, bulles utilisateur), vert (succès, meilleur prix), ambre (avertissements, état vide), fond `#f5f7fb` |
| Formes | Rayons 14–18 px, pastilles arrondies, ombres légères |
| Mouvement | Apparition douce des messages (0,22 s), soulèvement des cartes au survol, points animés pendant le traitement, défilement doux vers le dernier échange |
| Typographie | Police système ; titre d'accueil 2,1 rem, texte de réponse 0,97 rem |

Thème clair forcé (`.streamlit/config.toml`) : les composants HTML ont des couleurs fixes.

## Responsive

Colonne unique de 980 px maximum. Le carrousel défile horizontalement au doigt, la grille de la fiche passe de 4 à 2 colonnes sous 640 px et le titre d'accueil est réduit. Vérifié à 1280 px et 390 px ([08_mobile_accueil.png](screenshots/08_mobile_accueil.png), [09_mobile_resultats.png](screenshots/09_mobile_resultats.png)).

## Animations

Elles servent à **guider l'œil**, pas à décorer : chaque mouvement accompagne une arrivée, une action ou une attente.

| Où | Animation |
|---|---|
| Fond | Aurore bleue et violette qui dérive lentement (22 s) |
| Barre du haut | Verre dépoli fixé en haut · logo dont le halo respire · point vert « prêt » qui émet une onde |
| Accueil | Bandeau sombre avec 3 halos lumineux flottants · « commence ici. » en dégradé qui scintille · titre, texte et chiffres en cascade · **route animée** avec deux voitures qui la traversent (roues qui tournent, suspension, phare qui clignote, marquage qui défile) · suggestions en cascade, soulevées au survol avec une flèche qui glisse |
| Messages | Vos messages glissent depuis la droite (bulle en dégradé), ceux de l'assistant depuis la gauche · pastilles et puces qui « éclosent » |
| Recherche en cours | Petite voiture sur une piste pointillée + 3 cartes « fantômes » scintillantes (au moins 0,55 s) |
| Cartes | Entrée en cascade · au survol : soulèvement, reflet lumineux qui traverse la carte, voiture qui avance, **roues qui tournent** · badge « Meilleur prix » qui pulse · prix en dégradé |
| Fiche détaillée | La voiture entre depuis la gauche · les 8 caractéristiques apparaissent une à une |
| État vide | Loupe qui cherche |
| Saisie | Halo bleu-violet qui respire au focus · bouton d'envoi en dégradé, grossit au survol |

Toutes les animations sont désactivées si le système demande de **réduire les animations** (`prefers-reduced-motion`). Elles ne touchent que `transform` et `opacity` (et quelques ombres), ce qui reste fluide.

## Limites connues

- Les règles CSS s'appuient sur des sélecteurs internes de Streamlit (`stLayoutWrapper`, `stChatMessageAvatarUser`, `st-key-*`), vérifiés avec Streamlit 1.56.
- Pas de vraies photos de véhicules : c'est un choix délibéré de fiabilité.
- L'indicateur « Je recherche… » reste affiché au moins 0,55 s pour être perceptible (la recherche elle-même prend quelques millisecondes).
