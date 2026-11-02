#!/usr/bin/env python3
"""Variante LlamaIndex — `FunctionAgent` (tool-calling JSON).

Équivalent LlamaIndex de `agent_workflow2.py` (ToolCallingAgent de smolagents) :
même workflow (transcript FR -> résumé FR, points d'action FR, traductions EN),
mêmes quatre livrables, livrés dans un dossier dédié de `delivery/`.

PARADIGME : le LLM N'ÉCRIT PAS de code ; il émet des APPELS D'OUTILS en JSON
(function calling). Toute la mécanique commune vit dans `base_llamaindex.py`.

    python3 agent_llamaindex.py [chemin/vers/transcript.txt]
    OUTPUT_DIR=livrables python3 agent_llamaindex.py
"""

from __future__ import annotations

from llama_index.core.agent.workflow import FunctionAgent

from base_llamaindex import TOOLS, build_llm, run_llamaindex_workflow


def build_agent() -> FunctionAgent:
    """Spécificité de la variante : un FunctionAgent (appels d'outils JSON).

    disable_reasoning=True : gpt-5.6-terra exige reasoning_effort='none' avec des
    function tools sur /v1/chat/completions (sinon erreur 400).
    """
    return FunctionAgent(
        tools=TOOLS,
        llm=build_llm(disable_reasoning=True),
        system_prompt="Réponds en français. Avance en appelant les outils fournis.",
    )


def main() -> int:
    return run_llamaindex_workflow(
        build_agent,
        label="LlamaIndex FunctionAgent",
        default_output_dir="delivery/v4_llamaindex_function",
    )


if __name__ == "__main__":
    raise SystemExit(main())
