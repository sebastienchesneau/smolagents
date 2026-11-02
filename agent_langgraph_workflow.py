#!/usr/bin/env python3
"""Variante LangGraph — VRAI WORKFLOW métier (pas un agent qui boucle).

Contrairement à `agent_langgraph.py` (agent unique qui boucle librement sur des
outils), ici on ORCHESTRE nous-mêmes des étapes métier dans un ordre IMPOSÉ :

        START ─► summary ─► action_points ─► translation ─► END

Chaque nœud fait UN appel au LLM (génération de texte) et écrit son livrable ;
il n'y a aucune décision de l'agent sur « quel outil appeler » — le flux est
entièrement déterministe. C'est le vrai intérêt du graphe d'états : le contrôle.

L'état partagé transporte le transcript et les textes produits d'un nœud à l'autre.

    python3 agent_langgraph_workflow.py [chemin/vers/transcript.txt]
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from base_tools import (
    load_prompt,
    read_transcript,
    resolve_io,
    verify_deliverables,
    write_file,
)

SYSTEM = "Tu es un assistant rigoureux. Suis EXACTEMENT les consignes fournies. Réponds en français."


# --- L'état partagé : ce qui circule de nœud en nœud ------------------------
class WState(TypedDict):
    transcript_path: str
    output_dir: str
    transcript: str
    summary_fr: str
    actions_fr: str


# Pas de function tools ici -> pas besoin de reasoning_effort="none" (on peut
# garder le raisonnement du modèle actif).
def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-5.6-terra"),
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL"),
    )


def build_graph(llm: ChatOpenAI):
    """Trois nœuds métier enchaînés en séquence stricte."""

    def ask(prompt_step: str, material: str) -> str:
        """Un appel LLM : consignes de l'étape + matériau source."""
        instructions = load_prompt(prompt_step)
        resp = llm.invoke(
            [SystemMessage(content=SYSTEM), HumanMessage(content=f"{instructions}\n\n{material}")]
        )
        return resp.content

    # NŒUD 1 — résumé FR
    def summary_node(state: WState) -> dict:
        transcript = read_transcript(state["transcript_path"])
        summary = ask("summary", f"--- TRANSCRIPT ---\n{transcript}")
        write_file(os.path.join(state["output_dir"], "resume_fr.md"), summary)
        print("  [1/3] résumé FR écrit")
        return {"transcript": transcript, "summary_fr": summary}

    # NŒUD 2 — points d'action FR
    def actions_node(state: WState) -> dict:
        actions = ask("action_points", f"--- TRANSCRIPT ---\n{state['transcript']}")
        write_file(os.path.join(state["output_dir"], "points_action_fr.md"), actions)
        print("  [2/3] points d'action FR écrits")
        return {"actions_fr": actions}

    # NŒUD 3 — traduction EN du résumé ET des actions (2 appels)
    def translation_node(state: WState) -> dict:
        summary_en = ask(
            "translation",
            "Traduis UNIQUEMENT le RÉSUMÉ ci-dessous (titre `# Meeting Summary`).\n\n"
            f"--- RÉSUMÉ FR ---\n{state['summary_fr']}",
        )
        write_file(os.path.join(state["output_dir"], "summary_en.md"), summary_en)
        actions_en = ask(
            "translation",
            "Traduis UNIQUEMENT les POINTS D'ACTION ci-dessous (titre `# Action Items`).\n\n"
            f"--- POINTS D'ACTION FR ---\n{state['actions_fr']}",
        )
        write_file(os.path.join(state["output_dir"], "action_items_en.md"), actions_en)
        print("  [3/3] traductions EN écrites")
        return {}

    builder = StateGraph(WState)
    builder.add_node("summary", summary_node)
    builder.add_node("action_points", actions_node)
    builder.add_node("translation", translation_node)

    # Séquence STRICTE : summary -> action_points -> translation
    builder.add_edge(START, "summary")
    builder.add_edge("summary", "action_points")
    builder.add_edge("action_points", "translation")
    builder.add_edge("translation", END)

    return builder.compile()


def main() -> int:
    transcript_path, output_dir = resolve_io("delivery/v9_langgraph_workflow")
    if transcript_path is None:
        return 1
    if not os.getenv("OPENAI_API_KEY"):
        print("Aucun backend LLM configuré : OPENAI_API_KEY manquant.", file=sys.stderr)
        return 2

    graph = build_graph(build_llm())

    print("=" * 70)
    print("Variante : LangGraph (workflow métier summary -> actions -> translation)")
    print("Structure du graphe (Mermaid) :")
    print(graph.get_graph().draw_mermaid())
    print("=" * 70)

    start = time.perf_counter()
    print(f"[timing] Début : {datetime.now():%Y-%m-%d %H:%M:%S}")

    graph.invoke({"transcript_path": transcript_path, "output_dir": output_dir})

    print(f"[timing] Durée : {time.perf_counter() - start:.1f} s")

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
