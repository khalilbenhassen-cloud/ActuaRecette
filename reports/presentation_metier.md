# 🧪 ACTUARECETTE (v3.2)
### *La console de Gestion de Campagnes, d'Audit et de Recette Tarifaire de Masse*
*Support de Présentation Métier pour la MOA Actuariat Fonctionnelle (COMEX-Ready)*

---

## 📌 Slide 1 : Le Constat Opérationnel — L'Enfer d'Excel & Les Frictions Métiers

Dans le cycle de vie d'un produit d'assurance, le passage d'un nouveau tarif depuis les spécifications actuarielles vers les systèmes informatiques de production (Core Policy Systems) constitue une phase critique et à fort risque financier (Implementation Risk).

### Les difficultés réelles rencontrées par la MOA :
*   **L’Enfer d'Excel & d'Access :** Les recettes de masse se font sur des fichiers Excel monstrueux (> 100 Mo) ou des bases Access obsolètes qui rament, plantent et souffrent de formules brisées (`#VALEUR!`), incapables de comparer des portefeuilles complets (> 100 000 lignes).
*   **La dispersion des informations :** Le suivi des anomalies, des corrections et des runs successifs est éparpillé entre des e-mails, des fichiers Excel partagés et des tickets Jira IT disparates.
*   **La Chasse aux Centimes (Le bruit de recette) :** Des heures précieuses sont perdues à traquer des micro-écarts d'arrondis ou de taxes (TSCA, CatNat) de 1 ou 2 centimes, détournant l'attention des vrais bugs logiques de tarification.

---

## 📌 Slide 2 : La Vision ActuaRecette (v3.2) — La Sandbox de Validation Transparente

**ActuaRecette** est une application autonome, épurée et sécurisée conçue spécifiquement pour le **Business Analyst (BA) MOA Actuariat**. Elle sert de sas de validation hermétique entre l'Actuariat et la DSI, sans jamais interférer avec le code de production.

### La Philosophie : "Human-in-the-Loop" (L'anti-boîte noire)
*   **Contrôle total du BA :** L'outil n'effectue aucune correction automatique en arrière-plan. S'il détecte des anomalies de données, il propose des corrections dans un tableau comparatif (*Split-View*) et attend la validation manuelle en un clic.
*   **Zéro Jargon Technologique :** L'interface cache l'ingénierie logicielle (FastAPI, JSON, REST API) au profit d'un vocabulaire purement assurantiel (*Prime Pure, TSCA, Grilles de coefficients*).
*   **Divulgation Progressive (*Progressive Disclosure*) :** Les écrans ne sont pas surchargés. La synthèse et les KPIs macro sont affichés en premier ; les listes d'écarts unitaires, diagnostics et exports Jira restent masqués et ne se déploient qu'à la demande de l'actuaire.

---

## 📌 Slide 3 : L’Approche "Déclarative" par Mapping (Zéro Code)

La console n'embarque aucun code fiscal en dur ou de calcul réglementaire complexe, ce qui la rend instantanément universelle et résiliente :

```
┌────────────────────────────────┐       ┌────────────────────────────────┐
│   Fichier Actuariat (R&D)      │       │     Fichier Production DSI     │
│ Contient déjà TSCA_RC attendue │       │ Contient déjà TSCA_RC calculée │
└───────────────┬────────────────┘       └───────────────┬────────────────┘
                │                                        │
                └───────────────┐        ┌───────────────┘
                                ▼        ▼
                          [ Étape 2 : Mapping ]
                      "Associer TSCA_RC ➔ TSCA_RC"
                                │
                                ▼
                        [ Moteur In-Memory ]
                      Comparaison Face à Face
```

### Pourquoi c'est une révolution ergonomique ?
*   **Zéro développement complexe :** Vous n'avez pas besoin de coder ou de maintenir les lois fiscales changeantes dans l'outil.
*   **100% Universel :** L'outil fonctionne instantanément pour n'importe quel pays (France, Espagne, Maroc, etc.) et n'importe quel produit (Auto, Habitation, Santé, Prévoyance).
*   **Comparaison à la source :** Le BA MOA indique simplement à l'étape 2 quelles sont les colonnes à réconcilier. L'outil compare la colonne du fichier Actuariat avec celle du fichier DSI.

---

## 📌 Slide 4 : Le Parcours de Recette en 4 Étapes Visuelles

```
   [ ÉTAPE 1 ]              [ ÉTAPE 2 ]              [ ÉTAPE 3 ]              [ ÉTAPE 4 ]
 Ingestion & SAS        Mapping Déclaratif       Cascade de Taxes         Panier Jira
  Drag-and-drop          Liaisons en 1 clic      Waterfall interactif      Fiches de bug
 3 lignes de preview     Curseur de tolérance     Smart Bucketing doux     CSV témoins (BOM)
```

1.  **L'Ingestion (Le SAS) :** Double zone de dépôt épurée pour les fichiers Actuariat & DSI. Rendu visuel immédiat des 3 premières lignes pour vérification rapide sans surcharge.
2.  **Le Mapping Déclaratif :** Cartes de variables pour associer les clés de jointure et les primes. Un curseur interactif de tolérance permet d'éliminer le bruit décimal à la volée.
3.  **La Cascade de Taxes (Tax Waterfall) :** Graphique interactif en cascade comparant la décomposition moyenne des primes, complété par le *Smart Bucketing* (classement automatique des écarts réels par cause logique).
4.  **Le Panier de Bugs Jira :** Génération automatique de notes de bugs au format Markdown, épurées de tableaux indigestes, avec un sous-CSV restreint de 5 cas suspects encodé en `utf-8-sig` pour Excel Windows.

---

## 📌 Slide 5 : Inspirations UX/UI Premium

L'ergonomie d'ActuaRecette a été façonnée pour susciter l'adhésion immédiate des directions métiers :

*   **Akur8 (Pureté & Teintes) :** Charte graphique *Light Mode* apaisante (fond gris-bleu clair `#F8FAFC`, cartes de KPI blanches à ombrages discrets, police Inter).
*   **Qlik Sense (Panneau Associatif) :** Filtres interactifs appliquant le code couleur de Qlik (*Vert* = Segment sélectionné, *Blanc* = Anomalies associées à explorer, *Gris* = Segments conformes).
*   **Alteryx (Mapping Visuel) :** Alignement sémantique par cartes de colonnes interactives faciles à lier.
*   **Optalitix (Grid Diff) :** Tableau matriciel affichant la comparaison des coefficients tarifaires (ex : Bonus-Malus). Les cellules divergentes sont surlignées en vert doux (valeur DSI) et rouge barré (valeur attendue actuarielle).

---

## 📌 Slide 6 : ROI Métier — Ce que gagne l'Entreprise

*   **Time-to-Market Divisé par 10 :** La phase de recette actuarielle classique sur Excel passe de **6 à 8 semaines** à **quelques secondes** de calcul automatique en mémoire (10 millions de lignes traitées en 15 secondes).
*   **Protection de la Marge Technique :** Détection de 100% des anomalies logiques de tarification sur l'intégralité du portefeuille de test (zéro échantillonnage manuel), évitant les fuites financières de sous-tarification.
*   **Piste d'Audit Immuable (Solvabilité II) :** Archivage local automatique de chaque run de recette fonctionnelle, offrant une preuve de contrôle de l'Implementation Risk exigée par le Risk Management et les auditeurs.
*   **IT-Collaboration Pacifiée :** La DSI reçoit des tickets Jira clairs et documentés avec 5 cas unitaires précis à reproduire, sans le bruit de recette habituel lié aux centimes d'arrondis.
