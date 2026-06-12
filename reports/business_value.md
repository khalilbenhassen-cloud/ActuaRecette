# 📈 ActuaRecette : Analyse de Valeur Métier & ROI (Business Value)

**Destinataires :** Direction Générale, Direction Financière, Direction des Systèmes d'Information  
**Statut :** COMEX-Ready  
**Auteur :** Actuaire Conseil Senior & Direction des Investissements IT  
**Date :** 29 Mai 2026  

---

## 1. La Problématique Opérationnelle : Les Limites et Coûts de l'Existant (Legacy Excel)

Jusqu'à ce jour, le processus de recette actuarielle au sein de nos entités reposait sur l'utilisation de tableurs **Microsoft Excel** et de macros VBA locales. Ce mode opératoire traditionnel présente des limites structurelles critiques et un coût caché extrêmement élevé :

| Limitation Critique | Impact Opérationnel | Conséquence Financière |
| :--- | :--- | :--- |
| **Lenteur & Volumétrie** | Traitement limité et plantages fréquents d'Excel au-delà de 50 000 lignes d'assurés. | Campagnes de tests réduites à des échantillons arbitraires (risque d'anomalies non détectées). |
| **Surcharges par Faux Positifs** | Impossibilité de séparer les écarts logiques des écarts d'arrondis machine via VLOOKUP classique. | Fatigue des alertes chez les analystes MOA qui passent 80% de leur temps à auditer des déviations inoffensives de 0.01 €. |
| **Temps de Traitement** | 3 à 5 jours homme requis pour formater, fusionner et réconcilier une seule version tarifaire. | Retard sur le planning projet (Time-to-Market étalé) augmentant les frais de consulting externe. |

---

## 2. Quantification du ROI Financier : Productivité & Atténuation du Risque

Le déploiement d'**ActuaRecette** génère des retours financiers immédiats et mesurables, articulés autour de deux facteurs majeurs :

### A. Gains de Productivité MOA et Time-to-Market
*   **Temps de calcul unitaire :** Passage de **3 jours de traitement Excel** à **2 secondes de calcul** pour un portefeuille test standard de 100 000 profils d'assurés.
*   **Valorisation du temps de travail :** Pour une équipe de 5 analystes MOA effectuant en moyenne 15 campagnes de recette par an (releases tarifaires, correctifs DSI, évolutions réglementaires) :
    
    $$\text{Gain annuel} = 5 \text{ analystes} \times 15 \text{ runs/an} \times 3 \text{ jours/run} = 225 \text{ jours-hommes économisés/an}$$
    
    À un coût moyen interne journalier évalué à 400 € / jour-homme (ou TJM externe à 600 €) :
    
    > [!TIP]
    > **Économie directe estimée en productivité pure :** **~90 000 € à 135 000 € par an** de jours-hommes récupérés et réalloués à des tâches de modélisation actuarielle à forte valeur ajoutée.

### B. Atténuation du Risque d'Implémentation Financière (Risk Mitigation)
Une erreur de calcul apparemment mineure introduite par la DSI lors de l'intégration informatique d'un modèle peut passer inaperçue lors d'échantillonnages Excel manuels, mais s'avérer catastrophique à l'échelle du portefeuille réel.

> [!WARNING]
> **Scénario d'erreur classique de sous-tarification :**
> *   Une erreur de mapping ou de formule induit un déficit de tarification de **15,00 €** sur un segment cible de **50 000 contrats automobile** (ex: mauvaise application de la surprime Jeunes Conducteurs ou des taxes régionales).
> *   **Perte de prime brute annuelle immédiate :** $15,00\ \text{€} \times 50\ 000\ \text{contrats} = \mathbf{750\ 000\ \text{€}}$ de sous-tarification pure s'évaporant directement de la marge technique.
>
> ActuaRecette agit comme une **police d'assurance d'intégrité financière**, en interceptant ces anomalies à 100% de manière exhaustive dès les pré-environnements.

---

## 3. Impact Stratégique sur le Ratio Combiné (Combined Ratio)

Pour une compagnie d'assurance ou une mutuelle de taille intermédiaire affichant **300 Millions d'Euros** de primes émises annuelles, la réduction des risques de tarification et des coûts opérationnels impacte directement le **Ratio Combiné (CoS)**, indicateur roi de la performance technique et opérationnelle :

```
             ┌────────────────────────────────────────────────────────┐
             │       OPTIMISATION DU RATIO COMBINÉ (CoS)              │
             └───────────────────────────┬────────────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
         Marge Technique (S/P)                       Frais Généraux (F/P)
   - Éradication sous-tarification             - Automatisation de la recette
   - Maintien rigueur actuarielle              - Réduction consulting externe
   - Gains projetés : 0.15% à 0.30%            - Gains projetés : 0.05% à 0.10%
                   │                                           │
                   └─────────────────────┬─────────────────────┘
                                         ▼
                     GAIN PROJETÉ GLOBAL SUR LE RATIO COMBINÉ
                                 0.20% à 0.40%
                         (Soit 600 K€ à 1.2 M€ de gain)
```

1.  **Optimisation de la Marge Technique (Rapport S/P - Sinistres sur Primes) :**
    Le maintien de la rigueur actuarielle sur 100% du portefeuille évite les dérives de primes moyennes et protège le ratio de sinistralité.
    *Gain projeté :* **-0.15% à -0.30%** sur le ratio S/P.
2.  **Optimisation des Frais d'Acquisition et d'Administration (Rapport F/P - Frais sur Primes) :**
    L'automatisation absolue de la recette et la simplification des déclarations de bugs via Jira accélèrent les cycles IT et diminuent la charge de maintenance applicative DSI.
    *Gain projeté :* **-0.05% à -0.10%** sur le ratio F/P.

### Bilan de performance global
L'adoption de la plateforme ActuaRecette projette un gain global sur le ratio combiné de **0.20% à 0.40%**, représentant **600 000 € à 1 200 000 € d'économies annuelles récurrentes** pour notre portefeuille de 300 M€ de primes, garantissant l'amortissement technologique de l'outil dès sa première semaine de mise en production.
