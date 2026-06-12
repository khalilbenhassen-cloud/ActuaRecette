# 📄 Guide de l'Utilisateur ActuaRecette : Console Métier de Certification Tarifaire
### *Plateforme de Gouvernance Technique et d'Audit de Masse pour la MOA Actuariat*

---

> [!NOTE]
> **ActuaRecette** est un outil de gouvernance et de certification des calculs conçu spécifiquement pour la **MOA Actuariat** et les **Responsables Actuariat/Gestion des Risques**. Son objectif principal est de sécuriser le transfert de vos modèles de tarification (R&D) vers les systèmes d'information de production (DSI) afin d'éliminer le risque financier d'implémentation (*Implementation Risk*), en totale conformité avec les exigences de qualité des données de **Solvabilité II (Pilier 2)**.

---

## 🧭 1. Introduction & Vision Métier

Dans le cycle de commercialisation d'un contrat d'assurance, le passage d'un modèle actuariel (conçu sous forme de spécification fonctionnelle ou d'algorithme prototype) vers le moteur de facturation réel de la DSI comporte des risques d'écarts logiques. Des anomalies de code, des bruits d'arrondis de calcul ou des correspondances de tables erronées peuvent engendrer :
*   Une **sous-tarification** : perte de marge directe et silencieuse pour la compagnie.
*   Une **sur-tarification** : perte de compétitivité commerciale et dégradation de l'image de marque.

**ActuaRecette** offre un outil d'arbitrage automatisé pour :
1.  **Comparer instantanément des portefeuilles de masse** (allant jusqu'à un million d'assurés).
2.  **Distinguer automatiquement le simple bruit numérique** (micro-écarts de centimes dus aux arrondis de calcul) des **anomalies fonctionnelles fatales** (formules logiques erronées).
3.  **Collaborer de manière sécurisée** via un workflow structuré d'initiateur-approbateur (**Maker-Checker**).
4.  **Matérialiser les écarts en éléments de preuve** directement actionnables par les équipes de développement (fiches témoins et paniers d'anomalies Jira).

---

## 📥 2. Ingestion & Assainissement des Portefeuilles (Étape 1)

L'écran d'accueil d'une campagne vous propose de charger les fichiers de données nécessaires à l'analyse comparative.

```
+------------------------------------+      +------------------------------------+
| 📂 Portefeuille RÉFÉRENCE (MOA)    |      | 📂 Portefeuille PRODUCTION (DSI)    |
| Glissez-déposez le fichier CSV     |      | Glissez-déposez le fichier CSV     |
| (Ex: Tarifs attendus actuariat)    |      | (Ex: Primes calculées par le SI)   |
+------------------------------------+      +------------------------------------+
```

### 2.1 La Double Zone de Dépôt
*   **Fichier Référence (Actuariat) :** Contient les informations des assurés et la prime cible calculée ou validée par les actuaires.
*   **Fichier Production (DSI) :** Contient les mêmes assurés avec la prime réellement calculée par le moteur informatique de production.

### 2.2 Prévisualisation Méticuleuse (Zéro Clutter)
Dès le dépôt des fichiers, l'interface affiche une vue d'aperçu limitée aux **3 premières lignes**. Cela vous permet de valider d'un simple coup d'œil la structure de vos fichiers (noms des colonnes, séparateurs, cohérence des données) sans encombrer votre espace de travail.

### 2.3 La Vue Fractionnée d'Assainissement (*Split-View* de Nettoyage)
Les fichiers CSV issus de systèmes hétérogènes comportent souvent des imperfections de formatage (virgules à la place des points décimaux, espaces superflus, encodages Windows vs Linux). 
*   **Nettoyage automatique :** ActuaRecette applique des règles de tolérance lors du chargement (redressement des formats numériques, élimination des blancs).
*   **Visualisation Avant/Après :** Un volet dépliant rétractable (*expander*) vous présente le bilan de ce nettoyage. Vous visualisez de manière transparente le nombre de lignes redressées et le type de correction apporté, vous assurant de la pureté des données avant d'engager la comparaison.

---

## ⚙️ 3. Mapping Déclaratif & Règles Métier (Étape 2)

Une fois les données chargées, il est nécessaire de définir les correspondances pour guider le moteur de réconciliation unitaire.

### 3.1 Correspondance des Variables (Mapping)
Pour comparer les deux fichiers, vous devez déclarer trois variables clés dans le panneau de mapping (les autres variables techniques secondaires de taxes sont masquées par défaut pour préserver la clarté) :
1.  **Clé de Jointure Unique :** L'identifiant unique de l'assuré (ex: `ID_CLIENT`, `NUM_CONTRAT`) présent dans les deux fichiers.
2.  **Prime attendue (Actuariat) :** La colonne représentant la prime de référence (ex: `PRIME_REF`).
3.  **Prime calculée (Production) :** La colonne représentant la prime générée par le système informatique (ex: `PRIME_DSI`).

> [!TIP]
> **Recherche floue intelligente :** La console analyse les en-têtes et pré-sélectionne automatiquement les colonnes les plus probables, vous évitant de fastidieuses recherches manuelles.

### 3.2 Le Rule Builder (Contrôles de Qualité des Données)
Pour assurer la conformité Solvabilité II, vous pouvez définir des règles de cohérence métier sur les données des assurés. Si un dossier d'assuré ne respecte pas ces règles, il est marqué en anomalie de qualité :
*   **Limites d'âge :** Exclure ou signaler les assurés hors d'une tranche d'âge (ex: moins de 18 ans ou plus de 95 ans).
*   **Primes strictes :** S'assurer que les primes de référence sont strictement supérieures à zéro.
*   **Coefficients d'ajustement (CRM) :** Contrôler que le coefficient Bonus-Malus est compris dans les bornes réglementaires (ex: entre `0.50` et `1.50`).

### 3.3 Le Seuil de Tolérance Financière
Le moteur de calcul compare les primes au centime près. Cependant, deux moteurs peuvent calculer une prime avec des décimales internes différentes, générant de légers écarts d'arrondis sans importance fonctionnelle (ex: `0.01 €`).
*   À l'aide d'un **curseur interactif**, vous définissez le seuil de tolérance (ex: `0.05 €`).
*   Tout écart inférieur ou égal à ce seuil est automatiquement classé comme **Bruit d'arrondi** (conforme).
*   Tout écart supérieur est immédiatement isolé comme une **Anomalie financière**.

### 3.4 Bibliothèque de Scénarios (Modèles de Recette)
Pour éviter de redéfinir vos mappings et règles à chaque exécution, vous pouvez sauvegarder votre configuration sous forme de **Modèle de Recette**. 
*   **Sauvegarder :** Donnez un nom clair (ex: *Recette Auto V3.2*) pour stocker vos règles.
*   **Recharger :** Lors de la prochaine campagne, sélectionnez votre modèle dans la liste déroulante pour appliquer instantanément l'ensemble des correspondances et filtres de qualité.

---

## 🔍 4. Diagnostic, Exploration Visuelle & Panier de Bugs (Étape 3)

La phase d'exploration est conçue selon le principe de **divulgation progressive** : la synthèse macroscopique est affichée en premier, tandis que les détails d'audit s'activent uniquement sur demande.

```
   [ Synthèse Générale : Taux de Conformité (Gauges & Chiffres Clés) ]
                                 │
                                 ▼
         [ Cascade Financière Globale (Tax Waterfall Chart) ]
                                 │
                                 ▼
    [ Filtres Avancés par simple clic (Conformité, Âge, Tranche d'écart) ]
                                 │
                                 ▼
  [ Dossiers en Anomalies -> Clic -> Grille Matricielle de Coefficients ]
```

### 4.1 La Cascade Financière Globale (*Tax Waterfall*)
Ce graphique dynamique illustre visuellement la réconciliation des flux financiers. Il part de la masse totale de primes attendue par l'actuariat, applique les réductions, intègre les taxes intermédiaires, et comptabilise les écarts successifs pour aboutir au montant total calculé par la DSI. Cette représentation claire permet d'identifier immédiatement à quelle étape de calcul l'écart majeur se produit.

### 4.2 Les Filtres Interactifs de Diagnostic (Filtres type Qlik)
Affichés sous forme de cartes cliquables, ces filtres vous permettent de restreindre dynamiquement l'analyse :
*   **Par Statut :** Afficher uniquement les dossiers en *Anomalie logique*, en *Écart financier* ou *Conformes*.
*   **Par Tranche de Primes :** Cibler les petits contrats ou les grands risques.
*   **Par Nature d'Écart :** Isoler les bruits d'arrondis pour se concentrer uniquement sur les dysfonctionnements graves.

### 4.3 Le Grid Diff (Comparateur Matriciel de Coefficients)
Lorsqu'un écart de prime est détecté sur un assuré, l'origine provient souvent d'une grille de coefficients complexes (ex: tarification selon l'ancienneté et la zone géographique).
*   **Activation sur clic :** Cliquez sur un assuré en anomalie dans le tableau des écarts.
*   **La Matrice de coefficients :** Une grille double s'ouvre, superposant la grille attendue par la MOA (Référence) et la grille appliquée par le système (Production).
*   **Mise en évidence visuelle :** Les cellules de coefficients qui diffèrent sont surlignées en rouge orangé, vous indiquant la cellule exacte à l'origine de l'écart.

### 4.4 Le Panier de Bugs Jira (*Bug Cart*)
Plutôt que d'exporter l'intégralité des anomalies ou de rédiger des fiches de signalement manuelles :
*   **Sélection ciblée :** Cochez individuellement les dossiers d'assurés représentatifs d'une anomalie.
*   **Génération Jira :** Un bouton génère instantanément un texte au format standard **Jira Markdown**.
*   **Prêt à l'emploi :** Ce texte comprend l'explication en français d'assurance, la catégorie de risque (Critique/Moyen), et la fiche technique de l'assuré. Il vous suffit de le copier-coller dans votre outil de suivi de tickets Jira.

---

## 👥 5. Workflow Collaboratif, Signature & Clôture (Maker-Checker)

ActuaRecette impose une séparation stricte des rôles pour garantir l'indépendance de la validation.

### 5.1 Les Rôles Métier
*   **Actuaire MOA (Maker / Initiateur) :** Il charge les fichiers, configure les règles de tolérance, analyse les anomalies et prépare le dossier de recette.
*   **Responsable Actuariat (Checker / Approbateur) :** Il accède à la console en mode révision. Il consulte les taux de réussite, examine les observations de l'actuaire et prend la décision finale de certification de la campagne.

```
       +----------------------------+
       |   Actuaire MOA (Maker)     |  --> Ingestion, Diagnostic & Préparation
       +----------------------------+
                     │
                     ▼
       +----------------------------+
       | Responsable Actuariat      |  --> Audit final, Commentaire & Décision
       |         (Checker)          |  --> Signature formelle (Approuvé / Rejeté)
       +----------------------------+
```

### 5.2 Le Formulaire de Validation Métier
Dans l'onglet dédié `👥 Validation & Approbation` de l'Étape 3, le responsable de validation dispose d'un cadre formel pour prononcer sa sentence de recette :
*   **Nom du signataire :** Identification de l'autorité de validation.
*   **Décision :** Choix exclusif entre **Approuvé** (le modèle en production est conforme aux tolérances) et **Rejeté** (des écarts bloquants interdisent le déploiement).
*   **Observations de Recette :** Zone de texte libre pour formuler les réserves actuarielles ou les justifications techniques.

### 5.3 Le Registre Centralisé des Validations (*Audit Trail Global*)
Chaque signature de campagne alimente de manière inaltérable un **Registre de Validation d'Entreprise**.
*   Consultable au bas de l'écran *Historique*, ce grand livre répertorie chronologiquement toutes les campagnes clôturées.
*   Chaque ligne retrace l'identifiant de la campagne, l'auteur de la recette (Maker), le signataire (Checker), la décision de conformité, le taux de succès financier et la date exacte. 
*   Ce registre constitue le livrable parfait à présenter aux **commissaires aux comptes** ou aux **contrôleurs de l'ACPR** lors des audits Solvabilité II.

### 5.4 Le Kit Témoin de Recette (*Witness Kit*)
Pour permettre à la DSI de reproduire et corriger les écarts sans les surcharger avec des millions de lignes de données confidentielles :
*   **Export ZIP intelligent :** Un bouton vous permet de télécharger un fichier compressé unique (`witness_kit.zip`).
*   **Fiches Témoins à double ligne :** Le kit contient un rapport d'audit au format Markdown et les **5 fiches d'anomalies unitaires les plus critiques** sous forme de fichiers CSV individuels.
*   **Structure double ligne Excel native :** Chaque fichier CSV d'anomalie est formaté avec des séparateurs `;` et un encodage adapté pour s'ouvrir proprement dans Microsoft Excel Windows sans aucun problème de caractères. Il présente strictement **deux lignes** :
    *   *Ligne 1 (Référence) :* Les données d'origine et la prime théorique attendue par l'Actuariat.
    *   *Ligne 2 (Production) :* Les données traitées et la prime déviante calculée par le système informatique.
*   Cette structure épurée permet aux développeurs DSI d'isoler en 2 secondes la variable ou la formule en défaut.

---

## ❓ 6. Foire Aux Questions (FAQ) Métier

### Mon fichier CSV ne s'ouvre pas correctement ou comporte des caractères étranges. Que faire ?
> **Réponse :** ActuaRecette intègre un assainisseur automatique qui gère les principaux encodages (notamment `utf-8` et `Windows-1252` couramment utilisés par Excel). Si des caractères accentués restent illisibles, vérifiez simplement dans la Split-View d'Ingestion (Étape 1) que le format détecté correspond à vos attentes, ou demandez à votre exportateur de sauvegarder le fichier au format *CSV séparateur point-virgule (UTF-8)*.

### Qu'est-ce qu'un écart "logique" par opposition à un écart "financier" ?
> **Réponse :** 
> *   Un **Écart financier** est une divergence mathématique sur le montant final de la prime, mesuré après avoir appliqué le seuil de tolérance (ex: un écart de 15.00 € sur une prime).
> *   Une **Anomalie logique** provient du non-respect des règles de cohérence du *Rule Builder* (ex: un assuré déclaré avec un âge de 145 ans ou un coefficient Bonus-Malus négatif). Une anomalie logique est un défaut de qualité de données qui invalide le dossier, même si les primes coïncident.

### Comment transmettre les anomalies détectées à la DSI ?
> **Réponse :** Utilisez conjointement le **Panier de Bugs Jira** pour documenter vos tickets dans votre outil de suivi projet, et attachez-y le **Kit Témoin (Witness Kit ZIP)** contenant les fiches CSV unitaires à deux lignes. Ces éléments offrent une transparence totale aux développeurs de la DSI pour corriger la logique de programmation en quelques minutes.

### Comment sont traduits les messages d'erreurs techniques ?
> **Réponse :** ActuaRecette possède un traducteur intelligent intégré. Si un fichier d'entrée présente une erreur de traitement informatique (par exemple, une ligne tronquée ou une colonne introuvable), le système intercepte le message d'erreur brut et le traduit instantanément en français d'assurance clair (ex: *"La colonne de tarification attendue est absente du fichier"* au lieu de *"KeyError: 'PRIME_REF' at line 24"*).
