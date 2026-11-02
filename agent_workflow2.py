#!/usr/bin/env python3
"""Variante 2 — agent basé sur le `ToolCallingAgent` de smolagents.

PARADIGME : le LLM N'ÉCRIT PAS de code ; il émet des APPELS D'OUTILS structurés
(function calling, en JSON), un appel à la fois.

Tout le reste (outils, choix du modèle, boucle d'exécution, vérification des
livrables) vit dans `base.py`. Ce fichier ne contient que ce qui est PROPRE à la
variante ToolCallingAgent : la classe d'agent, la formulation de la tâche, et le
paramètre `reasoning_effort='none'` exigé par gpt-5.6-terra en tool-calling.

    python agent_workflow2.py [chemin/vers/transcript.txt]
"""

from __future__ import annotations

from smolagents import ToolCallingAgent

from base import load_prompt, read_transcript, run_workflow, write_file

# Prompt propre au ToolCallingAgent : on raisonne en « appels d'outils », pas en
# code. Le contenu rédigé est passé en argument `content` de `write_file`.
TASK_TEMPLATE = """\
Tu es un assistant qui traite le compte rendu d'une réunion.

La langue initiale du transcript est le FRANÇAIS.

IMPORTANT :
- Tu disposes RÉELLEMENT des outils `read_transcript`, `load_prompt` et
  `write_file` : les fichiers EXISTENT et sont accessibles via ces outils. Ne
  refuse jamais la tâche et n'affirme jamais que tu ne peux pas y accéder.
- Avance en APPELANT les outils, un appel à la fois. Pour chaque étape, charge
  d'abord ses consignes détaillées avec `load_prompt`, puis applique-les.
- Le contenu rédigé (résumé, points d'action, traductions) doit être passé en
  argument `content` de `write_file`.

Déroulé du workflow :

0. Appelle `read_transcript` avec path="{transcript_path}".

1. ÉTAPE « summary » :
   - appelle `load_prompt` avec step="summary" ;
   - rédige le résumé en français selon ces consignes ;
   - appelle `write_file` avec path="{output_dir}/resume_fr.md" et le résumé.

2. ÉTAPE « action_points » :
   - appelle `load_prompt` avec step="action_points" ;
   - extrais les points d'action en français selon ces consignes ;
   - appelle `write_file` avec path="{output_dir}/points_action_fr.md".

3. ÉTAPE « translation » :
   - appelle `load_prompt` avec step="translation" ;
   - traduis en anglais le résumé ET les points d'action selon ces consignes ;
   - appelle `write_file` avec path="{output_dir}/summary_en.md" (résumé EN) ;
   - appelle `write_file` avec path="{output_dir}/action_items_en.md" (actions EN).

4. Termine avec `final_answer` en donnant la liste des quatre fichiers écrits.

N'invente aucune information qui ne figure pas dans le transcript.
"""


def build_agent(model) -> ToolCallingAgent:
    """Spécificité de la variante : un ToolCallingAgent (appels d'outils JSON)."""
    return ToolCallingAgent(
        tools=[load_prompt, read_transcript, write_file],
        model=model,
        max_steps=12,
    )


def main() -> int:
    # gpt-5.6-terra exige reasoning_effort='none' avec des function tools sur
    # /v1/chat/completions (sinon erreur 400).
    return run_workflow(
        build_agent,
        TASK_TEMPLATE,
        label="ToolCallingAgent",
        default_output_dir="delivery/v2_toolcalling",
        openai_extra={"reasoning_effort": "none"},
    )


if __name__ == "__main__":
    raise SystemExit(main())
