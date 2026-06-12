# ActuaRecette : Enterprise Actuarial UAT & Spec Governance Platform

**ActuaRecette** est une plateforme SaaS B2B ultra-premium dédiée à la **gouvernance technique et à la recette fonctionnelle (UAT)** des modèles de tarification d'assurance. Elle permet aux actuaires conseils, risk managers, et équipes MOA d'auditer la qualité des portefeuilles, de réconcilier de manière unitaire les calculs financiers complexes, et d'isoler instantanément les anomalies de programmation de la DSI pour respecter les exigences de conformité réglementaire de **Solvabilité II**.

---

## 1. Executive Summary & Vision

Dans le cycle de vie d'un produit d'assurance, le transfert du modèle actuariel (prototype R&D) vers les systèmes d'information opérationnels (SI de production) constitue un risque financier majeur appelé **« Implementation Risk »**. Les décalages logiques, les bruits d'arrondis de calcul, ou les mappings de données corrompus provoquent des écarts silencieux de sous-tarification (pertes directes de primes) ou de sur-tarification (perte de parts de marché).

**ActuaRecette** élimine ce risque en fournissant un outil d'arbitrage automatisé capable de comparer des millions de lignes de primes en quelques secondes, de séparer automatiquement le bruit numérique des anomalies fatales, et de traduire chaque écart en ticket de bug documenté prêt à être exporté dans Jira, sous contrôle d'un processus strict **Maker-Checker** Pilier 2.

---

## 2. Diagramme d'Architecture Technique

La plateforme repose sur une architecture découplée, modulaire et hautement performante reliant l'interface utilisateur, la validation de schémas, les moteurs mathématiques et la persistance locale :

```mermaid
graph TD
    A["IHM Streamlit Frontend (Port 8501)"] -->|Requêtes HTTP + En-têtes SSO| B["FastAPI Backend Server (Port 8000)"]
    B -->|Pydantic Validation (api/schemas.py)| C["Moteur Métier Actuariel (src/)"]
    C -->|Calcul & Réconciliation Actuarielle| E["Variance Analyzer (src/variance_analyzer.py)"]
    C -->|Gouvernance des Anomalies & Justifications| F["Anomaly Manager (src/anomaly_manager.py)"]
    F -->|Sauvegarde et Verrouillage Cryptographique| G[("data/uat_runs/ (JSON verrouillés + Integrity Hash)")]
    
    style A fill:#0F172A,stroke:#3B82F6,stroke-width:2px,color:#F1F5F9
    style B fill:#1E293B,stroke:#10B981,stroke-width:2px,color:#F1F5F9
    style C fill:#1E293B,stroke:#F59E0B,stroke-width:2px,color:#F1F5F9
    style E fill:#334155,stroke:#94A3B8,stroke-width:1px,color:#F1F5F9
    style F fill:#334155,stroke:#94A3B8,stroke-width:1px,color:#F1F5F9
    style G fill:#0F172A,stroke:#EC4899,stroke-width:2px,color:#F1F5F9
```

---

## 3. Les Fonctionnalités Majeures (v6.0)

### 🔒 3.1. Cloisonnement & Gouvernance SecOps
* **Authentification SSO & RBAC Sécurisée (SEC-01)** : Remplacement de la transmission d'en-têtes HTTP en texte brut par un mécanisme de signature de payload d'identité via jeton Bearer signé avec une clé HMAC-SHA256. Toute falsification ou expiration du jeton (24h) invalide la requête.
* **Cloisonnement strict par LOB (Line of Business) (SEC-02)** : Un utilisateur ne peut interagir qu'avec les campagnes de son LOB assigné. Le cloisonnement est obligatoire au niveau des APIs d'historique, de qualité des données (`/dq-report`), et de l'IHM.
* **Workflow Maker-Checker (Ségrégation des tâches)** : La validation d'une campagne est obligatoirement soumise au principe de non-cumul (Maker ≠ Checker), contrôlé au niveau du backend API.
* **Verrouillage et Contrôle d'Intégrité Cryptographique** : Les campagnes validées sont scellées en base et sur disque. Une vérification de non-altération (contrôle de hash cryptographique `signature_hash` à la volée) est opérée à chaque chargement de run historique pour alerter en cas de modification manuelle des fichiers.
* **Suivi de présence & Nettoyage de Session** : Les heartbeats de présence utilisateur sont persistés en base SQLite dans la table `active_sessions`, avec un mécanisme de nettoyage périodique automatique éliminant les sessions inactives de plus de 90 secondes.

### ⚙️ 3.2. Moteur Actuariel & Multi-Domaines
* **Support Multi-Domaines** : Tarification et recette disponibles pour 5 domaines métiers : **Prime**, **Sinistre**, **Réserve**, **Contrat**, et **Réassurance**.
* **Moteur de Règles Dynamiques** : Chargement et validation automatique des règles depuis une base SQLite locale (`data/actuarecette.db`), conformes aux directives Solvabilité II.
* **Garantie d'Intégrité des Données d'Ingestion** : Sauvegarde bit-à-bit du flux d'importation CSV brut et conversion transparente Excel vers CSV avec synchronisation automatique du fingerprint SHA-256 pour bloquer les tentatives de manipulation.

---

## 4. Parcours Utilisateur : Le Wizard à 4 Étapes

Le cœur de la recette s'effectue dans l'**Espace de Travail** interactif doté d'un stepper dynamique bloqué en avant tant que les exigences de l'étape active ne sont pas validées :

1. **Importation** : Chargement des fichiers source Référence (Actuariat) et Production (DSI). Déclaration obligatoire de provenance DSI (traçabilité de custody) pour débloquer les étapes suivantes.
2. **Contrôles** : Configuration du mapping des variables clés et calcul automatique de la réconciliation.
3. **Analyse** : Profilage statistique Plotly de la distribution des écarts, documentation des justifications individuelles par dossier non-conforme, et génération/copie simplifiée de tickets Jira pré-formatés.
4. **Certification** : Passage au crible de la checklist de conformité du Validateur, signature et attribution d'un numéro officiel unique ACPR (ex : `CERT-LOB_AUTO_PART-YYYYMM-001`), et téléchargement du kit de preuve final (Rapport PDF formel & kit témoin ZIP).

---

## 5. Guide de Démarrage Rapide

### 📋 Étape 5.1 : Installation des Dépendances
Installez les bibliothèques requises :
```bash
pip install pandas numpy streamlit fastapi uvicorn pydantic requests plotly watchfiles openpyxl
```

### ⚙️ Étape 5.2 : Initialisation du Pipeline et de la Base de Données
Exécutez le script d'initialisation pour générer les jeux de données réalistes, migrer le schéma de base de données SQLite et charger les règles réglementaires actives :
```bash
python run_pipeline.py
```

### 🌐 Étape 5.3 : Lancement du Serveur FastAPI (Backend)
Démarrez le serveur REST API en configurant le chemin python :
```bash
$env:PYTHONPATH='c:\Users\hp\Documents\ActuaRecette'; python api/main.py
```

### 🖥️ Étape 5.4 : Lancement de l'Application Streamlit (Frontend)
Dans un second terminal, lancez le serveur Streamlit sur le point d'entrée correct :
```bash
$env:PYTHONPATH='c:\Users\hp\Documents\ActuaRecette'; python -m streamlit run dashboard/app.py
```

---

## 👥 6. Comptes de Test SSO

Pour tester les différents rôles et la politique de sécurité de l'application, connectez-vous avec l'un des comptes de test du registre local :

| Identifiant SSO | Nom Utilisateur | Rôle Métier | LOBs Visibles (Cloisonnement) |
| :--- | :--- | :--- | :--- |
| `maker.junior` | Actuaire junior (Maker) | **Actuaire MOA** (Maker) | `LOB_AUTO_PART` (Auto uniquement) |
| `maker.senior` | Actuaire senior | **Actuaire MOA** (Maker) | `LOB_INCENDIE_RD` (Incendie uniquement) |
| `checker` | Validateur Technique (Checker) | **Validateur** (Checker) | Tous les LOBs |
| `manager` | Responsable Métier (Manager) | **Responsable MOA** (Manager) | Tous les LOBs |

---

## 🧪 7. Exécution des Tests de Non-Régression & Sécurité

Une suite complète de plus de 30 scripts de tests unitaires, d'intégration et de sécurité valide l'ensemble des fonctionnalités de la plateforme.

Pour lancer le nouvel audit de sécurité et de robustesse RBAC (SEC-01/02) :
```bash
python tests/test_security_rbac.py
```

Pour exécuter toute la suite et valider la conformité globale :
```bash
python scratch/run_all_tests.py
```
