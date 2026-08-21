# Journal debord du projet

J'ai ouvert mon CTO il y a tout juste un an. L'idée d'analyser mon comportement sur les marchés financiers m'est apparue lorsque j'eu assez d'historique pour regarder ce qu'il s'est passé dans mes données.
J'ai entendu parler de pas mal de biais recontrés en bourse (FOMO, biais des couts irrécupérables...).
Après un an, c'est le moment de faire un retour d'expérience et de créer un outil pour analyser en continu les différentes transactions réalisées.


## Qualité de données

La première analyse de mon CTO s'est fait environ trois mois après l'ouverture du compte. Initialement, je ne passais que par l'application mobile. L'extraction décrite comme format CSV n'apparaissait que sous forme de table, je devais donc faire des captures d'écran. 
Les données des premiers mois était donc sous forme d'image contenant une table.
Afin de récupérer ces tables au format CSV, j'ai du faire de l'OCR (Optical Caracter Recognition). Mais l'OCR peut avoir ces limites et intégrer du bruit dans les données (par exemple ajouter un 0 au code ISIN).


### Causes

- Après comparaison entre mon portefeuille actuel et le portefeuille déduit des données extraites, je constate que c'est l'extraction du mois de septembre qui est incomplète.
- Je contaste également une coquille au niveau du ISIN d'une action


### Solution

Pour compléter les données manquantes, je vais m'appuyer sur les avis d'opérés (par action) envoyés en fin de journée. Et pour corriger les codes ISIN, je vais m'assurer de la cohérence du numéro (doit contenur 12 caractères).

Les deux causes trouvées pourront permettre de réaliser des tests automatiques pour vérifier la qualité des données lorsqu'elles seront traitées par l'API.

## Développement

Pour le développement de l'outils de suivi, je dois m'assurer que les données sont de bonnes qualités pour garantir la qualité de l'analyse.
