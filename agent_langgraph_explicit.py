#!/usr/bin/env python3
"""Variante LangGraph — graphe d'états CONSTRUIT À LA MAIN (nœuds + arêtes).

Même workflow et mêmes livrables que `agent_langgraph.py`, mais on n'utilise PAS
le prebuilt `create_react_agent` : on assemble explicitement le StateGraph pour
RENDRE VISIBLES les nœuds et les arêtes.

`create_react_agent` n'est qu'un raccourci qui construit EXACTEMENT ce graphe :

        START
          │
          ▼
      ┌────────┐   (pas d'appel d'outil)
      │ agent  │ ─────────────────────────► END
      └────────┘
        ▲   │ (le LLM demande un/des outils)
        │   ▼
      ┌────────┐
      │ tools  │
      └────────┘
     (retour vers agent avec le résultat de l'outil)

C'est la boucle agent <-> outils, rendue graphe. La condition agent -> (tools|END)
est l'arête conditionnelle : tant que le LLM appelle des outils, on reboucle ;
dès qu'il répond sans outil, on sort.

    python3 agent_langgraph_explicit.py [chemin/vers/transcript.txt]
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

# On réutilise les outils et la construction du modèle de la variante prebuilt.
from agent_langgraph import TOOLS, build_llm
from base_tools import TASK_TEMPLATE, resolve_io, verify_deliverables

SYSTEM_PROMPT = "Réponds en français. Avance en appelant les outils fournis."


def build_graph():
    """Assemble le graphe à la main : 2 nœuds (agent, tools) + les arêtes."""
    # Le LLM, avec les outils « liés » : il saura émettre des appels d'outils.
    llm_with_tools = build_llm().bind_tools(TOOLS)

    # --- NŒUD 1 : « agent » = un tour de LLM --------------------------------
    def agent_node(state: MessagesState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [llm_with_tools.invoke(messages)]}

    # --- NŒUD 2 : « tools » = exécute les outils demandés par le LLM --------
    tool_node = ToolNode(TOOLS)

    # --- Le graphe : état partagé = la liste des messages -------------------
    builder = StateGraph(MessagesState)

    # Les NŒUDS
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)

    # Les ARÊTES
    builder.add_edge(START, "agent")          # entrée -> agent
    builder.add_conditional_edges(            # agent -> tools  OU  agent -> END
        "agent",
        tools_condition,                      # "tools" si le LLM a appelé un outil, sinon END
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "agent")        # tools -> agent (on reboucle)

    return builder.compile()


def main() -> int:
    transcript_path, output_dir = resolve_io("delivery/v7_langgraph_explicit")
    if transcript_path is None:
        return 1

    try:
        graph = build_graph()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # On AFFICHE la structure du graphe (nœuds + arêtes) en syntaxe Mermaid.
    print("=" * 70)
    print("Variante : LangGraph (graphe explicite)")
    print("Structure du graphe (Mermaid) :")
    print(graph.get_graph().draw_mermaid())
    print("=" * 70)

    task = TASK_TEMPLATE.format(transcript_path=transcript_path, output_dir=output_dir)

    start_dt = datetime.now()
    start_perf = time.perf_counter()
    print(f"[timing] Début : {start_dt:%Y-%m-%d %H:%M:%S}")

    result = graph.invoke(
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
