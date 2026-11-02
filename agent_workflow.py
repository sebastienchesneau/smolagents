#!/usr/bin/env python3
"""Variante 1 — agent basé sur le `CodeAgent` de smolagents.

PARADIGME : le LLM ÉCRIT DU CODE PYTHON qui appelle les outils. L'interpréteur
exécute ce code à chaque pas.

Tout le reste (outils, choix du modèle, boucle d'exécution, vérification des
livrables) vit dans `base.py`. Ce fichier ne contient que ce qui est PROPRE à la
variante CodeAgent : la classe d'agent et la formulation de la tâche.

    python agent_workflow.py [chemin/vers/transcript.txt]
"""

from __future__ import annotations

from smolagents import CodeAgent

from base import load_prompt, read_transcript, run_workflow, write_file

# Prompt propre au CodeAgent : on insiste sur « réponds avec un bloc de code ».
TASK_TEMPLATE = """\
Tu es un assistant qui traite le compte rendu d'une réunion.

La langue initiale du transcript est le FRANÇAIS.

IMPORTANT :
- Tu disposes RÉELLEMENT des outils `read_transcript`, `load_prompt` et
  `write_file` : les fichiers EXISTENT et sont accessibles via ces outils. Ne
  refuse jamais la tâche et n'affirme jamais que tu ne peux pas y accéder.
- Pour CHAQUE étape, commence par charger ses instructions détaillées avec
  `load_prompt(<nom_étape>)`, puis applique-les scrupuleusement.
- Réponds TOUJOURS avec un bloc de code Python ; n'écris jamais une réponse en
  texte seul tant que la tâche n'est pas terminée.

Déroulé du workflow :

0. Lis le transcript : `read_transcript("{transcript_path}")`.

1. ÉTAPE « summary » :
   - charge ses consignes : `load_prompt("summary")` ;
   - rédige le résumé en français en suivant ces consignes ;
   - écris-le : `write_file("{output_dir}/resume_fr.md", <résumé_fr>)`.

2. ÉTAPE « action_points » :
   - charge ses consignes : `load_prompt("action_points")` ;
   - extrais les points d'action en français en suivant ces consignes ;
   - écris-les : `write_file("{output_dir}/points_action_fr.md", <actions_fr>)`.

3. ÉTAPE « translation » :
   - charge ses consignes : `load_prompt("translation")` ;
   - traduis en anglais le résumé ET les points d'action en suivant ces consignes ;
   - écris : `write_file("{output_dir}/summary_en.md", <résumé_en>)` ;
   - écris : `write_file("{output_dir}/action_items_en.md", <actions_en>)`.

4. Donne comme réponse finale la liste des quatre fichiers écrits.

N'invente aucune information qui ne figure pas dans le transcript.
"""


def build_agent(model) -> CodeAgent:
    """Spécificité de la variante : un CodeAgent (le LLM écrit du code)."""
    return CodeAgent(
        tools=[load_prompt, read_transcript, write_file],
        model=model,
        max_steps=10,
    )


def main() -> int:
    return run_workflow(
        build_agent,
        TASK_TEMPLATE,
        label="CodeAgent",
        default_output_dir="delivery/v1_codeagent",
    )


if __name__ == "__main__":
    raise SystemExit(main())
