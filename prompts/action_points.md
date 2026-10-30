# Étape — Points d'action (français)

Objectif : extraire les points d'action concrets de la réunion, EN FRANÇAIS.

Ce qu'est un point d'action :
- Un engagement ou une tâche à réaliser qui ressort explicitement du transcript.
- À distinguer des simples constats ou opinions : ne garde que ce qui appelle
  une action.

Pour CHAQUE point d'action, précise, quand l'information existe dans le
transcript :
- le **responsable** (la personne en charge) ;
- l'**action** à réaliser, formulée avec un verbe à l'infinitif ;
- l'**échéance** (date ou délai). Si elle n'est pas précisée, indique
  explicitement « Échéance : non précisée » plutôt que d'inventer.

Consignes de forme :
- Commence le fichier par le titre Markdown exact : `# Points d'action`.
- Puis une liste à puces Markdown (`- `), un point d'action par puce.
- Mets le responsable en gras, par exemple :
  `- **Marc** : envoyer le planning détaillé. Échéance : vendredi.`
- Trie les actions par responsable si c'est pertinent.

Règle absolue : n'invente aucune action, aucun responsable ni aucune échéance
absents du transcript.
