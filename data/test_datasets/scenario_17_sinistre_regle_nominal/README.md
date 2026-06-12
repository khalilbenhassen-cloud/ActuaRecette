# Scénario 17 : Domaine Sinistre - Mécanisme A (Règle dynamique - Nominal)

## Objectif
Valider le mécanisme A (Formule dynamique) de réconciliation en comparant le coût DSI déclaré avec la somme des règlements et provisions.

## Contexte
- Portefeuille : Automobile Particuliers (`LOB_AUTO_PART`)
- Domaine : Sinistre
- Seuil de tolérance du domaine : **3.0 %**
- Colonnes DSI : `PAIEMENTS_DSI`, `PSAP_DSI`, `SINISTRE_DSI` (total).
- Règle dynamique à configurer : `SINISTRE_DSI == PAIEMENTS_DSI + PSAP_DSI` (Tolérance = 0.00).

## Comportement attendu dans ActuaRecette
1. Créer une campagne pour le LOB **"Automobile Particuliers"** et le domaine **"Sinistre"**.
2. Mappez la clé sur : `ID_SINISTRE`
3. Mappez le Sinistre Référence sur : `SINISTRE_REF`
4. Mappez le Sinistre Production sur : `SINISTRE_DSI`
5. Allez dans **Configuration des Règles** (Administration) et ajoutez une règle :
   - Cible : `SINISTRE_DSI`
   - Formule : `PAIEMENTS_DSI + PSAP_DSI`
   - Opérateur : `==`
   - Tolérance : `0.00`
6. La réconciliation doit produire un taux de conformité de **100%**.
