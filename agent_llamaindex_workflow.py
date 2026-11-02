#!/usr/bin/env python3
"""Variante LlamaIndex — VRAI WORKFLOW via le système `Workflow` natif.

Contrairement à `agent_llamaindex.py` (agent qui boucle sur des outils), on
utilise ici le moteur `Workflow` de LlamaIndex, piloté par ÉVÉNEMENTS : chaque
`@step` consomme un événement et en émet un autre, ce qui impose l'ordre :

    StartEvent ─► summarize ─► SummaryReady ─► extract_actions
                                              ─► ActionsReady ─► translate ─► StopEvent

Chaque étape fait un simple appel de génération au LLM (pas de tool-calling) et
écrit son livrable. Le flux est déterministe, défini par les types d'événements.

    python3 agent_llamaindex_workflow.py [chemin/vers/transcript.txt]
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from base_llamaindex import build_llm
from base_tools import (
    load_prompt,
    read_transcript,
    resolve_io,
    verify_deliverables,
    write_file,
)


# --- Les événements qui circulent entre les étapes --------------------------
class SummaryReady(Event):
    transcript: str
    output_dir: str
    summary: str


class ActionsReady(Event):
    output_dir: str
    summary: str
    actions: str


class TranscriptWorkflow(Workflow):
    """Workflow à 3 étapes : résumé -> points d'action -> traduction."""

    def __init__(self, llm, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm

    async def _ask(self, prompt_step: str, material: str) -> str:
        """Un appel de génération : consignes de l'étape + matériau source."""
        instructions = load_prompt(prompt_step)
        resp = await self.llm.acomplete(f"{instructions}\n\n{material}")
        return str(resp)

    # ÉTAPE 1 — résumé FR (déclenchée par le StartEvent)
    @step
    async def summarize(self, ev: StartEvent) -> SummaryReady:
        transcript = read_transcript(ev.transcript_path)
        summary = await self._ask("summary", f"--- TRANSCRIPT ---\n{transcript}")
        write_file(os.path.join(ev.output_dir, "resume_fr.md"), summary)
        print("  [1/3] résumé FR écrit")
        return SummaryReady(
            transcript=transcript, output_dir=ev.output_dir, summary=summary
        )

    # ÉTAPE 2 — points d'action FR (déclenchée par SummaryReady)
    @step
    async def extract_actions(self, ev: SummaryReady) -> ActionsReady:
        actions = await self._ask(
            "action_points", f"--- TRANSCRIPT ---\n{ev.transcript}"
        )
        write_file(os.path.join(ev.output_dir, "points_action_fr.md"), actions)
        print("  [2/3] points d'action FR écrits")
        return ActionsReady(
            output_dir=ev.output_dir, summary=ev.summary, actions=actions
        )

    # ÉTAPE 3 — traduction EN du résumé ET des actions (déclenchée par ActionsReady)
    @step
    async def translate(self, ev: ActionsReady) -> StopEvent:
        summary_en = await self._ask(
            "translation",
            "Traduis UNIQUEMENT le RÉSUMÉ ci-dessous (titre `# Meeting Summary`).\n\n"
            f"--- RÉSUMÉ FR ---\n{ev.summary}",
        )
        write_file(os.path.join(ev.output_dir, "summary_en.md"), summary_en)
        actions_en = await self._ask(
            "translation",
            "Traduis UNIQUEMENT les POINTS D'ACTION ci-dessous (titre `# Action Items`).\n\n"
            f"--- POINTS D'ACTION FR ---\n{ev.actions}",
        )
        write_file(os.path.join(ev.output_dir, "action_items_en.md"), actions_en)
        print("  [3/3] traductions EN écrites")
        return StopEvent(result="Workflow terminé : 4 livrables écrits.")


def main() -> int:
    transcript_path, output_dir = resolve_io("delivery/v10_llamaindex_workflow")
    if transcript_path is None:
        return 1
    try:
        # Pas de function tools -> reasoning du modèle laissé actif.
        llm = build_llm(disable_reasoning=False)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("=" * 70)
    print("Variante : LlamaIndex Workflow (summarize -> extract_actions -> translate)")
    print(f"Transcript : {transcript_path}")
    print(f"Sortie     : {output_dir}")
    print("=" * 70)

    start = time.perf_counter()
    print(f"[timing] Début : {datetime.now():%Y-%m-%d %H:%M:%S}")

    wf = TranscriptWorkflow(llm=llm, timeout=240)

    async def _run():
        return await wf.run(transcript_path=transcript_path, output_dir=output_dir)

    result = asyncio.run(_run())

    print(f"[timing] Durée : {time.perf_counter() - start:.1f} s")
    print(f"\nRésultat : {result}\n")

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
