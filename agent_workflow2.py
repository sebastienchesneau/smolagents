#!/usr/bin/env python3
"""Variante 2 de l'agent : basée sur le paradigme AGENTIQUE « tool-calling ».

Même workflow et mêmes livrables que `agent_workflow.py`, mais l'agent n'écrit
PLUS de code Python : il utilise un `ToolCallingAgent` qui appelle les outils via
des appels de fonction structurés (JSON), un par étape.

    read_transcript -> load_prompt -> write_file (x4)

Les outils, la sélection du modèle et la liste des livrables sont réutilisés tels
quels depuis `agent_workflow.py` (source unique de vérité).

Utilisation :
    python agent_workflow2.py                      # transcript_fr.txt par défaut
    python agent_workflow2.py chemin/vers/transcript.txt
"""

from __future__ import annotations

import os
import sys

from smolagents import ToolCallingAgent

from agent_workflow import (
    DELIVERABLES,
    build_model,
    load_prompt,
    read_transcript,
    write_file,
)

# --------------------------------------------------------------------------- #
# Tâche — formulée pour un agent tool-calling (pas de bloc de code)
# --------------------------------------------------------------------------- #

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
    """Crée le ToolCallingAgent (paradigme tool-calling) avec les outils."""
    return ToolCallingAgent(
        tools=[load_prompt, read_transcript, write_file],
        model=model,
        max_steps=12,
    )


def main() -> int:
    transcript_path = os.path.abspath(
        sys.argv[1] if len(sys.argv) > 1 else "transcript_fr.txt"
    )
    output_dir = os.path.abspath(os.getenv("OUTPUT_DIR", "delivery"))

    if not os.path.exists(transcript_path):
        print(f"Transcript introuvable : {transcript_path}", file=sys.stderr)
        return 1

    try:
        # gpt-5.6-terra exige reasoning_effort='none' avec des function tools
        # sur /v1/chat/completions (sinon erreur 400).
        model = build_model(openai_extra={"reasoning_effort": "none"})
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    agent = build_agent(model)
    task = TASK_TEMPLATE.format(
        transcript_path=transcript_path, output_dir=output_dir
    )

    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RAPPORT FINAL (ToolCallingAgent)")
    print("=" * 70)
    print(result)

    # Vérification : les quatre livrables ont-ils bien été écrits ?
    missing = [
        name
        for name in DELIVERABLES
        if not os.path.exists(os.path.join(output_dir, name))
    ]
    if missing:
        print(
            "\nÉCHEC : fichiers manquants dans "
            f"{output_dir} -> {', '.join(missing)}\n"
            "Le modèle n'a pas produit tous les livrables. Relancez la commande.",
            file=sys.stderr,
        )
        return 3

    print(f"\nOK : {len(DELIVERABLES)} fichiers écrits dans {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
