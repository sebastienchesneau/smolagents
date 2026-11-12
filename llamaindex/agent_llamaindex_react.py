#!/usr/bin/env python3
"""Variante LlamaIndex — `ReActAgent` (boucle texte Thought/Action/Observation).

Même workflow et mêmes quatre livrables que `agent_llamaindex.py`, mais avec le
paradigme ReAct : le LLM n'émet PAS de function tools JSON ; il raisonne en
TEXTE (Thought -> Action -> Observation) que LlamaIndex PARSE pour en déduire
l'outil à appeler.

Conséquence : la contrainte `reasoning_effort="none"` de gpt-5.6-terra (qui ne
vaut que pour les *function tools*) ne s'applique pas -> on garde le raisonnement
actif (disable_reasoning=False).

    python3 agent_llamaindex_react.py [chemin/vers/transcript.txt]
    OUTPUT_DIR=livrables python3 agent_llamaindex_react.py
"""

from __future__ import annotations

from llama_index.core.agent.workflow import ReActAgent

# --- bootstrap : racine du dépôt importable (base.py / base_tools.py y restent) ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from base_llamaindex import TOOLS, build_llm, run_llamaindex_workflow


def build_agent() -> ReActAgent:
    """Spécificité de la variante : un ReActAgent (boucle texte ReAct)."""
    return ReActAgent(
        tools=TOOLS,
        llm=build_llm(disable_reasoning=False),
        system_prompt="Réponds en français. Avance en appelant les outils fournis.",
    )


def main() -> int:
    return run_llamaindex_workflow(
        build_agent,
        label="LlamaIndex ReActAgent",
        default_output_dir="delivery/v5_llamaindex_react",
    )


if __name__ == "__main__":
    raise SystemExit(main())
