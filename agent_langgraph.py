#!/usr/bin/env python3
"""Variante LangGraph — `create_react_agent` (tool-calling JSON).

Équivalent LangGraph de `agent_workflow2.py` / `agent_llamaindex.py` : même
workflow (transcript FR -> résumé FR, points d'action FR, traductions EN), mêmes
quatre livrables, livrés dans un dossier dédié de `delivery/`.

PIÈGE DE NOM : le helper s'appelle `create_react_agent`, mais il utilise le
TOOL-CALLING natif de l'API (JSON), PAS la boucle texte ReAct de LlamaIndex.
C'est donc l'équivalent du `FunctionAgent` / `ToolCallingAgent`.

Idée propre à LangGraph : l'agent est un GRAPHE D'ÉTATS (nœud « modèle » <->
nœud « outils »), exécuté de façon synchrone via `.invoke(...)`.

    python3 agent_langgraph.py [chemin/vers/transcript.txt]
    OUTPUT_DIR=livrables python3 agent_langgraph.py
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from base_tools import (
    TASK_TEMPLATE,
    load_prompt,
    read_transcript,
    resolve_io,
    verify_deliverables,
    write_file,
)

# Les mêmes fonctions natives, enveloppées façon LangChain (StructuredTool infère
# le schéma des arguments depuis les annotations de type et le docstring).
TOOLS = [
    StructuredTool.from_function(load_prompt),
    StructuredTool.from_function(read_transcript),
    StructuredTool.from_function(write_file),
]


def build_llm() -> ChatOpenAI:
    """Construit le LLM LangChain pointant sur le modèle du projet.

    reasoning_effort="none" : create_react_agent fait du tool-calling (function
    tools), donc gpt-5.6-terra l'exige sur /v1/chat/completions (même contrainte
    que smolagents ToolCallingAgent et LlamaIndex FunctionAgent).
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Aucun backend LLM configuré : définissez OPENAI_API_KEY "
            "(+ OPENAI_MODEL optionnel) dans le fichier .env."
        )
    model_id = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    print(f"[model] ChatOpenAI : {model_id}")
    return ChatOpenAI(
        model=model_id,
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL"),  # None -> endpoint OpenAI par défaut
        reasoning_effort="none",
    )


def main() -> int:
    transcript_path, output_dir = resolve_io("delivery/v6_langgraph")
    if transcript_path is None:
        return 1

    try:
        llm = build_llm()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # create_react_agent construit le graphe d'états (modèle <-> outils).
    agent = create_react_agent(
        llm,
        TOOLS,
        prompt="Réponds en français. Avance en appelant les outils fournis.",
    )
    task = TASK_TEMPLATE.format(transcript_path=transcript_path, output_dir=output_dir)

    print("=" * 70)
    print("Variante : LangGraph create_react_agent")
    print(f"Transcript : {transcript_path}")
    print(f"Sortie     : {output_dir}")
    print("=" * 70)

    start_dt = datetime.now()
    start_perf = time.perf_counter()
    print(f"[timing] Début : {start_dt:%Y-%m-%d %H:%M:%S}")

    # Exécution synchrone du graphe. recursion_limit : garde-fou sur le nombre de
    # tours de boucle (le workflow en fait ~6, on laisse de la marge).
    result = agent.invoke(
        {"messages": [("user", task)]},
        {"recursion_limit": 50},
    )

    elapsed = time.perf_counter() - start_perf
    print(f"[timing] Durée : {elapsed:.1f} s")
    print(f"\nRéponse de l'agent :\n{result['messages'][-1].content}\n")

    missing = verify_deliverables(output_dir)
    if missing:
        print(f"ÉCHEC : fichiers manquants : {missing}", file=sys.stderr)
        return 3

    print("OK : les quatre livrables ont été écrits :")
    for name in ("resume_fr.md", "points_action_fr.md", "summary_en.md", "action_items_en.md"):
        print(f"  - {os.path.join(output_dir, name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
