# DOTOMI-TRADE — Frontend

Interface web complète du système, construite en React (Vite) + Tailwind
CSS. Consomme l'API du backend (`../backend`) — voir le README racine pour
le guide d'hébergement complet des deux parties ensemble.

---

## 1. Direction de design

L'interface s'éloigne volontairement de l'esthétique "dashboard crypto
néon sur fond sombre" associée par défaut au trading. À la place :
l'identité visuelle d'un **instrument de précision** — cadrans, aiguilles,
hairlines fines, vocabulaire de mesure plutôt que de SaaS générique.

Contraintes de design imposées et respectées :

- **Fond clair, papier chaud** (`#FAF8F3`) — jamais de noir pur, violet,
  ou bleu nuit comme couleur structurante.
- **Aucun émoji, nulle part.** Toute l'iconographie est en SVG dessiné à
  la main (`src/icons/index.jsx`), pas de librairie d'icônes générique.
- **Couleurs fonctionnelles réservées au sens** : vert profond
  (`#173404`) pour autorisé/positif, ambre (`#9C6B14`) pour
  surveiller/faible, rouge brique (`#7A1F1F`) pour rejeté/négatif —
  jamais utilisées de façon décorative ailleurs.
- **Typographie** : Fraunces (serif display, pour les chiffres clés et
  titres — évoque les tableaux de cotation imprimés), Inter (UI/labels),
  IBM Plex Mono (toutes les données tabulaires : prix, scores).
- **Élément signature** : `ScoreDial` (`src/components/ScoreDial.jsx`), le
  score 0-100 rendu comme un cadran à aiguille avec les zones de seuil
  dessinées en arcs colorés, plutôt qu'une barre de progression générique.

---

## 2. Structure

```
frontend/
├── src/
│   ├── icons/index.jsx          # Toutes les icônes SVG sur mesure
│   ├── components/
│   │   ├── Sidebar.jsx           # Navigation, reprend les pages du cahier des charges produit
│   │   ├── ScoreDial.jsx         # Élément signature : cadran à aiguille
│   │   ├── StatusBadge.jsx       # Badge Autorisé/Surveiller/Faible/Rejeté
│   │   ├── ReasonList.jsx        # Liste des raisons (positives/blocages)
│   │   ├── SetupRow.jsx          # Ligne compacte pour les listes de setups
│   │   └── Layout.jsx            # Card, PageHeader, EmptyState, Stat...
│   ├── pages/                    # Une page par module du cahier des charges
│   │   ├── DashboardPage.jsx
│   │   ├── ScannerPage.jsx
│   │   ├── RecommendationPage.jsx
│   │   ├── ValidationPage.jsx
│   │   ├── RiskCenterPage.jsx
│   │   ├── JournalPage.jsx
│   │   ├── AnalyticsPage.jsx
│   │   ├── PlaybookPage.jsx
│   │   ├── AlertsPage.jsx
│   │   └── SettingsPage.jsx
│   ├── lib/
│   │   ├── api.js                # Client HTTP vers le backend
│   │   ├── usePolling.js         # Hook de rafraîchissement périodique
│   │   └── format.js             # Formatage prix/score/statut
│   ├── App.jsx                   # Routeur (HashRouter, simple à héberger statiquement)
│   └── index.css                 # Tokens de couleur, polices, focus visible
├── tailwind.config.js             # Palette complète commentée
└── .env.example
```

---

## 3. Pages et ce qu'elles montrent

| Page | Contenu |
|---|---|
| Dashboard | Meilleure opportunité actuelle, état du risque, raisons du score |
| Scanner | Lance un scan à la demande sur un symbole, détail des 7 sous-scores |
| Trade Recommendation | Top trade + 2 alternatives, justification complète |
| Validation Engine | Checklist des règles obligatoires pour un setup donné |
| Risk Center | Calculateur de sizing local + plafonds actifs |
| Journal | Historique des trades réellement journalisés |
| Analytics | Statistiques et courbe d'équité — vides tant qu'il n'y a pas de trades réels |
| Playbook | Patterns gagnants mesurés sur l'historique réel |
| Alertes | Santé système par composant et par marché |
| Profil & règles | Configuration active du moteur (lecture seule en V1) |

---

## 4. Installation et lancement

```bash
npm install
cp .env.example .env
# VITE_API_URL doit pointer vers le backend (http://localhost:8000 en local)

npm run dev      # serveur de développement, http://localhost:5173
npm run build    # build de production -> dossier dist/
npx oxlint src/  # lint
```

---

## 5. Vérifications effectuées avant livraison

- `npm run build` : succès, 0 erreur.
- `npx oxlint src/` : 0 warning, 0 erreur.
- Vérification automatisée (script Python) de l'absence totale d'émojis
  dans `src/`.
- Vérification manuelle de l'absence de couleurs interdites (noir pur,
  violet, bleu nuit) dans le code Tailwind/CSS.

**Limite honnête** : le rendu visuel réel dans un navigateur n'a pas pu
être vérifié par capture d'écran depuis l'environnement où ce code a été
préparé (aucun outil de ce type disponible ici). Lancez `npm run dev` et
ouvrez `http://localhost:5173` vous-même en premier pour confirmer que le
rendu correspond à l'intention avant de considérer l'interface comme
définitivement validée — en particulier l'alignement du cadran `ScoreDial`
et le rendu des polices Google Fonts chargées à distance.

---

## 6. Notes techniques

- **Routage** : `HashRouter` (URLs en `#/scanner` plutôt que `/scanner`) —
  choix volontaire pour rester compatible avec un hébergement statique
  simple (GitHub Pages, S3...) sans configuration serveur de réécriture
  d'URL. À remplacer par `BrowserRouter` si l'hébergement cible (Vercel,
  Netlify) gère nativement le fallback SPA, pour des URLs plus propres.
- **Polling, pas de WebSocket** : les pages se rafraîchissent par
  intervalle (`usePolling`, 5 à 15 secondes selon la page). Suffisant pour
  cette V1 ; un WebSocket serait une amélioration naturelle pour du
  vraiment temps réel.
- **Aucune donnée fabriquée côté frontend** : toutes les pages
  Analytics/Playbook affichent un état vide explicite tant que le backend
  ne retourne pas de trades réels — cohérent avec le garde-fou du backend
  (jamais de statistique inventée).
