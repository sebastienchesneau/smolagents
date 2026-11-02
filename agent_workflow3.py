#!/usr/bin/env python3
"""Variante 3 — workflow MULTI-AGENT (hiérarchique) avec smolagents.

PARADIGME : au lieu d'un seul agent qui fait tout, un agent « MANAGER » délègue
le travail à trois AGENTS SPÉCIALISÉS (« managed agents »). Chaque sous-agent a
un `name` + une `description` ; le manager les appelle comme s'il s'agissait
d'outils, leur confie une tâche, et récupère leur résultat.

    manager
      ├── summarizer        -> résumé FR          -> delivery/resume_fr.md
      ├── action_extractor  -> points d'action FR -> delivery/points_action_fr.md
      └── translator        -> traductions EN     -> delivery/summary_en.md
                                                      delivery/action_items_en.md

Les outils, le choix du modèle, la boucle d'exécution et la vérification des
livrables sont réutilisés depuis `base.py`. Ici, le `agent_factory` construit les
sous-agents PUIS le manager, et renvoie le manager à `run_workflow`.

    python agent_workflow3.py [chemin/vers/transcript.txt]
"""

from __future__ import annotations

from smolagents import CodeAgent

from base import load_prompt, read_transcript, run_workflow, write_file

# --------------------------------------------------------------------------- #
# Instructions propres à chaque sous-agent (son « métier »)
# --------------------------------------------------------------------------- #

SUMMARIZER_INSTRUCTIONS = """\
Tu es spécialisé dans la rédaction de résumés de réunion EN FRANÇAIS.
Méthode : (1) `load_prompt("summary")` pour tes consignes, (2) `read_transcript`
pour lire le transcript, (3) rédige le résumé du CONTENU RÉEL de la réunion, puis
(4) `write_file` pour l'enregistrer. Réponds toujours avec un bloc de code Python.

ATTENTION : le résumé doit porter sur ce qui se dit DANS le transcript (les
personnes, leurs propos, les décisions, les chiffres). Ne décris JAMAIS la
consigne ni le fait que « le transcript a été lu / doit être résumé » : produis
directement le résumé du fond, en citant des éléments concrets du transcript.
"""

ACTION_EXTRACTOR_INSTRUCTIONS = """\
Tu es spécialisé dans l'extraction de points d'action EN FRANÇAIS.
Méthode : charge d'abord tes consignes avec `load_prompt("action_points")`, lis
le transcript avec `read_transcript`, extrais les points d'action en suivant les
consignes, puis écris-les avec `write_file`. Réponds toujours en code Python.
"""

TRANSLATOR_INSTRUCTIONS = """\
Tu es spécialisé dans la traduction du français vers l'anglais.
Méthode : charge d'abord tes consignes avec `load_prompt("translation")`, lis les
fichiers français avec `read_transcript` (il lit n'importe quel fichier), traduis
en suivant les consignes, puis écris les fichiers anglais avec `write_file`.
Réponds toujours avec un bloc de code Python.
"""

# --------------------------------------------------------------------------- #
# Tâche confiée au MANAGER (il orchestre, il ne rédige pas lui-même)
# --------------------------------------------------------------------------- #

MANAGER_TASK = """\
Tu es le MANAGER d'une équipe de trois agents spécialisés que tu peux appeler :
- `summarizer`        : rédige le résumé FR d'un transcript ;
- `action_extractor`  : extrait les points d'action FR d'un transcript ;
- `translator`        : traduit des fichiers français vers l'anglais.

Transcript source : {transcript_path}
Dossier de sortie : {output_dir}

Tu n'écris PAS toi-même le contenu : tu délègues, puis tu vérifies. Déroulé :

1. Appelle `summarizer` en lui demandant de lire le transcript
   "{transcript_path}", de produire le résumé FR et de l'écrire dans
   "{output_dir}/resume_fr.md".

2. Appelle `action_extractor` en lui demandant de lire le transcript
   "{transcript_path}", d'extraire les points d'action FR et de les écrire dans
   "{output_dir}/points_action_fr.md".

3. Appelle `translator` en lui demandant de traduire :
   - "{output_dir}/resume_fr.md"        -> "{output_dir}/summary_en.md"
   - "{output_dir}/points_action_fr.md" -> "{output_dir}/action_items_en.md"

4. Donne comme réponse finale la liste des quatre fichiers produits.
"""


def build_agent(model) -> CodeAgent:
    """Construit les trois sous-agents spécialisés, puis le manager.

    C'est LA spécificité de cette variante : une hiérarchie d'agents plutôt
    qu'un agent unique. Le manager reçoit les sous-agents via `managed_agents`.
    """
    common_tools = [load_prompt, read_transcript, write_file]

    summarizer = CodeAgent(
        tools=common_tools,
        model=model,
        name="summarizer",
        description=(
            "Rédige un résumé en français d'un transcript de réunion et l'écrit "
            "dans un fichier. Indique-lui le chemin du transcript et le chemin "
            "du fichier de sortie."
        ),
        instructions=SUMMARIZER_INSTRUCTIONS,
        max_steps=6,
    )

    action_extractor = CodeAgent(
        tools=common_tools,
        model=model,
        name="action_extractor",
        description=(
            "Extrait les points d'action en français d'un transcript de réunion "
            "et les écrit dans un fichier. Indique-lui le chemin du transcript "
            "et le chemin du fichier de sortie."
        ),
        instructions=ACTION_EXTRACTOR_INSTRUCTIONS,
        max_steps=6,
    )

    translator = CodeAgent(
        tools=common_tools,
        model=model,
        name="translator",
        description=(
            "Traduit des fichiers Markdown du français vers l'anglais. "
            "Indique-lui, pour chaque fichier, le chemin source (FR) et le "
            "chemin de sortie (EN)."
        ),
        instructions=TRANSLATOR_INSTRUCTIONS,
        max_steps=6,
    )

    # Le manager n'a pas besoin d'outils propres : il pilote ses sous-agents.
    manager = CodeAgent(
        tools=[],
        model=model,
        managed_agents=[summarizer, action_extractor, translator],
        max_steps=12,
    )
    return manager


def main() -> int:
    return run_workflow(
        build_agent,
        MANAGER_TASK,
        label="Manager (multi-agent)",
        default_output_dir="delivery/v3_multiagent",
    )


if __name__ == "__main__":
    raise SystemExit(main())
