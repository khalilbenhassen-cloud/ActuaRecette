# ⚖️ ActuaRecette : Note de Gouvernance, Conformité & Risques (AI Governance)

**Destinataires :** Direction des Risques, Comité d'Audit, Compliance Officer & Audit Externe  
**Statut :** ACPR / COMEX-Ready  
**Auteur :** Chief Risk Officer & Expert en Conformité Réglementaire Assurantielle  
**Date :** 29 Mai 2026  

---

## 1. Contexte Réglementaire : Solvabilité II & Normes Actuarielles Internationales (ASOP 56)

Dans le cadre du contrôle interne et de la supervision des modèles quantitatifs appliqués à la tarification et aux provisions des entreprises d'assurance, la gouvernance des modèles est soumise à deux cadres réglementaires stricts :

### A. Solvabilité II (Pilier 2 - Exigences qualitatives de gouvernance)
La directive européenne impose aux assureurs de mettre en œuvre un système robuste de gestion des risques opérationnels. Cela implique une **validation indépendante de tout modèle informatique** calculant des engagements ou déterminant la politique commerciale (tarification). La direction technique doit apporter la preuve matérielle que la logique actuarielle validée n'a subi aucune dérive lors de sa traduction en systèmes d'information (DSI).

### B. Norme Professionnelle ASOP 56 (Actuarial Standard of Practice No. 56 - Actuarial Models)
Cette norme internationale régit le développement, l'utilisation et la validation des modèles actuariels. Elle exige expressément des procédures de contrôle rigoureuses :
*   **Independent Replication (Réplication Indépendante) :** Obligation d'éprouver le système cible via un modèle miroir développé de façon indépendante pour déceler les biais logiciels de codage.
*   **Data Quality Assessment (Audit de Qualité des Données) :** Nécessité d'auditer l'intégrité et la pertinence des bases d'entrées avant toute modélisation financière, sous peine de rendre les résultats caducs (*« Garbage in, garbage out »*).

> [!IMPORTANT]
> **ActuaRecette** répond nativement aux exigences d'**ASOP 56** et de **Solvabilité II** en réalisant une double réplication systématique (algorithmique et structurelle) et en formalisant un contrôle de qualité ETL automatisé avant chaque phase de réconciliation tarifaire.

---

## 2. Les Piliers de Conformité d'ActuaRecette : Traçabilité, Audit & RGPD

Pour garantir un niveau de contrôle interne COMEX-Ready et opposable aux commissaires aux comptes ou aux contrôleurs de l'ACPR, la plateforme s'appuie sur trois piliers technologiques :

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PILIERS DE CONFORMITÉ                           │
├──────────────────────────┬────────────────────────┬────────────────────┤
│      TRAÇABILITÉ         │    PROCÈS-VERBAL       │  SÉCURITÉ RGPD     │
│   Piste d'audit JSON     │   Rapport de recette   │  Anonymisation et  │
│   immuable et archivée   │   certifié et signé    │  données pseudonyme│
└──────────┬───────────────┴──────────┬─────────────┴────────┬───────────┘
           │                          │                      │
           ▼                          ▼                      ▼
    Fichiers stockés          KPIs consolidés,       Clés client
    dans data/uat_runs        liste d'anomalies,     techniques (ID_CLIENT)
    avec hash et date         diagnostics experts    sans données PII
```

### A. Une Piste d'Audit Absolue et Immuable
Chaque campagne de recette fonctionnelle exécutée par la MOA génère un fichier de run historique persistant au format JSON stocké dans le répertoire sécurisé `data/uat_runs/`. 
*   **Horodatage ISO intégré :** Date et heure précises de la recette enregistrées de façon inaltérable.
*   **Versionnage système :** Traçabilité exacte de la version du moteur de calcul utilisé.
*   **Archivage des configurations :** Enregistrement des colonnes mappées et de la tolérance exacte (ex: 0.05 €) appliquée lors du run.

### B. Génération du Procès-Verbal de Recette Officiel (Certifié COMEX)
L'outil consigne de manière exhaustive le bilan qualité :
*   Le résumé quantitatif des dossiers testés et déclarés conformes.
*   Le taux de succès global.
*   L'écart financier maximal unitaire et le cumul des deltas absolus (indicateur indispensable pour évaluer le provisionnement comptable du risque d'implémentation).
*   La liste complète des anomalies fatales avec leur diagnostic technique.
Ce rapport consolidé fait office de Procès-Verbal officiel de recette, prêt à être signé et transmis au Comité des Risques et d'Audit.

### C. Protection des Données Personnelles et RGPD
Afin de respecter la réglementation européenne (RGPD), la plateforme de recette manipule exclusivement des données pseudonymisées ou anonymisées :
*   **ID_CLIENT technique :** Utilisation de codes clients générés et anonymes (ex: `C001`, `C002`) exempts de toute donnée personnelle (pas de nom, prénom, numéro de sécurité sociale ou adresse postale physique).
*   **Cloisonnement des serveurs :** Le serveur d'API FastAPI s'exécute localement en circuit fermé interne sans aucune fuite ni exportation de données vers des services tiers externes Cloud.

---

## 3. La Ségrégation des Tâches : Le Cloisonnement Maker-Checker

Pour prévenir les risques de conflits d'intérêts et d'erreurs de manipulation, ActuaRecette structure sa gouvernance opérationnelle selon le principe de la ségrégation stricte des tâches : le flux **« Maker-Checker »** (Initiateur-Validateur) :

```
   ┌────────────────────────────────┐
   │             MAKER              │ (Actuaire MOA / Analyste Recette)
   │  - Dépose les CSV de tests     │
   │  - Mappe les colonnes          │
   │  - Ajuste le seuil de tolérance│
   │  - Génère le PV provisoire     │
   └───────────────┬────────────────┘
                   │
                   ▼ Soumission pour validation
   ┌────────────────────────────────┐
   │            CHECKER             │ (Actuaire en Chef / Risk Manager)
   │  - Audite le PV de recette     │
   │  - Valide les écarts d'arrondis│
   │  - Signe numériquement le PV   │
   │  - Autorise la mise en prod    │
   └────────────────────────────────┘
```

1.  **Le Maker (L'Analyste Recette MOA) :**
    *   *Rôle :* Il est responsable de l'exécution des tests. Il dépose les extractions de production DSI, aligne les colonnes de mapping, effectue le contrôle de qualité initial et initie les comparaisons financières unitaire-à-unitaire.
    *   *Livrable :* Il soumet le rapport d'anomalies global et propose le procès-verbal de recette provisoire.
2.  **Le Checker (L'Actuaire en Chef ou Risk Manager) :**
    *   *Rôle :* Il détient le pouvoir d'approbation indépendant. Il examine le procès-verbal généré par le *Maker*, vérifie la légitimité des bruits d'arrondis tolérés, audite la liste des anomalies fatales et s'assure que les diagnostics d'écarts ont été correctement résolus par la DSI.
    *   *Livrable :* Il appose sa signature numérique sur le procès-verbal final de recette et autorise formellement le déploiement opérationnel de la release tarifaire sur le serveur de production.
