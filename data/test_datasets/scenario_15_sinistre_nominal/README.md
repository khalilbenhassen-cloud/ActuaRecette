# Scénario 15 : Domaine Sinistre - Cas nominal (Sans écart)

## Objectif
Valider la réconciliation de qualité et du data profiling sur le domaine **Sinistre** sans aucun écart de tarification ou de règlement.

## Contexte
- Portefeuille : Automobile Particuliers (`LOB_AUTO_PART`)
- Domaine : Sinistre
- Seuil de tolérance du domaine : **3.0 %**
- Noms de colonnes : `ID_SINISTRE` (clé), `SINISTRE_REF` (référence), `SINISTRE_DSI` (production).

## Comportement attendu dans ActuaRecette
1. Sélectionner le LOB **"Automobile Particuliers"** et le domaine **"Sinistre"** à la création.
2. Mappez la clé sur : `ID_SINISTRE`
3. Mappez le Sinistre Référence sur : `SINISTRE_REF`
4. Mappez le Sinistre Production sur : `SINISTRE_DSI`
5. La réconciliation produit un taux de conformité de **100%**.
