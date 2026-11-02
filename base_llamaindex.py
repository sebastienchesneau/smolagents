#!/usr/bin/env python3
"""Socle commun aux variantes LlamaIndex (pendant de `base.py` pour smolagents).

Produit les mêmes quatre livrables que le projet smolagents (résumé FR, points
d'action FR, summary EN, action items EN) à partir d'un transcript français.

Les outils, le `TASK_TEMPLATE` et la logique de chemins/vérification viennent du
socle NEUTRE `base_tools.py` (partagé avec la variante LangGraph). Ce module
n'ajoute que ce qui est spécifique à LlamaIndex : l'enveloppe `FunctionTool`, le
choix du modèle `OpenAILike`, et la boucle d'exécution asynchrone.

Les variantes importent depuis ce module :
    from base_llamaindex import TOOLS, build_llm, run_llamaindex_workflow
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from llama_index.core.tools import FunctionTool
from llama_index.llms.openai_like import OpenAILike

from base_tools import (
    TASK_TEMPLATE,
    load_prompt,
    read_transcript,
    resolve_io,
    verify_deliverables,
    write_file,
)

# Outils prêts à être passés à un agent LlamaIndex (FunctionAgent / ReActAgent).
TOOLS = [
    FunctionTool.from_defaults(fn=load_prompt),
    FunctionTool.from_defaults(fn=read_transcript),
    FunctionTool.from_defaults(fn=write_file),
]

# --------------------------------------------------------------------------- #
# Sélection du modèle
# --------------------------------------------------------------------------- #


def build_llm(*, disable_reasoning: bool) -> OpenAILike:
    """Construit le LLM LlamaIndex à partir du `.env` du projet.

    OpenAILike (et non la classe OpenAI) : gpt-5.6-terra n'est pas un modèle
    « connu » de LlamaIndex, OpenAILike évite la validation du nom.

    Args:
        disable_reasoning: si True, force `reasoning_effort="none"`. Requis par
            gpt-5.6-terra en mode *function tools* (FunctionAgent). Inutile pour
            ReAct, qui ne passe pas de function tools à l'API.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Aucun backend LLM configuré : définissez OPENAI_API_KEY "
            "(+ OPENAI_MODEL optionnel) dans le fichier .env."
        )
    extra = {"reasoning_effort": "none"} if disable_reasoning else {}
    model_id = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    print(f"[model] OpenAILike : {model_id}")
    return OpenAILike(
        model=model_id,
        api_key=os.environ["OPENAI_API_KEY"],
        api_base=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        is_chat_model=True,
        is_function_calling_model=True,
        context_window=128000,
        additional_kwargs=extra,
    )


# --------------------------------------------------------------------------- #
# Boucle d'exécution partagée (pendant de run_workflow de base.py)
# --------------------------------------------------------------------------- #


def run_llamaindex_workflow(agent_factory, *, label, default_output_dir) -> int:
    """Exécute le workflow commun aux variantes LlamaIndex.

    Args:
        agent_factory: fonction `() -> agent` (c'est ce qui change entre
            FunctionAgent et ReActAgent).
        label: nom de la variante, affiché dans l'en-tête.
        default_output_dir: dossier de sortie propre à la variante (surchargé
            par la variable d'env OUTPUT_DIR).

    Codes de retour : 0 OK · 1 transcript introuvable · 2 pas de backend LLM ·
    3 livrables manquants.
    """
    transcript_path, output_dir = resolve_io(default_output_dir)
    if transcript_path is None:
        return 1

    try:
        agent = agent_factory()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    task = TASK_TEMPLATE.format(transcript_path=transcript_path, output_dir=output_dir)

    print("=" * 70)
    print(f"Variante : {label}")
    print(f"Transcript : {transcript_path}")
    print(f"Sortie     : {output_dir}")
    print("=" * 70)

    start_dt = datetime.now()
    start_perf = time.perf_counter()
    print(f"[timing] Début : {start_dt:%Y-%m-%d %H:%M:%S}")

    # agent.run(...) démarre le workflow au moment de l'appel et exige une boucle
    # asyncio déjà active -> on l'appelle DANS une coroutine (pas asyncio.run
    # directement sur agent.run(...), qui l'appellerait hors boucle).
    async def _run():
        return await agent.run(task)

    response = asyncio.run(_run())

    elapsed = time.perf_counter() - start_perf
    print(f"[timing] Durée : {elapsed:.1f} s")
    print(f"\nRéponse de l'agent :\n{response}\n")

    missing = verify_deliverables(output_dir)
    if missing:
        print(f"ÉCHEC : fichiers manquants : {missing}", file=sys.stderr)
        return 3

    print("OK : les quatre livrables ont été écrits :")
    for name in ("resume_fr.md", "points_action_fr.md", "summary_en.md", "action_items_en.md"):
        print(f"  - {os.path.join(output_dir, name)}")
    return 0
