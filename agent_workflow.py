#!/usr/bin/env python3
"""Agent smolagents (Hugging Face) qui traite un transcript de réunion.

Workflow implémenté par l'agent, à partir d'un transcript en français. À chaque
étape, l'agent charge d'abord ses consignes détaillées via load_prompt(étape) :
    1. Lire le transcript.
    2. Étape « summary »       -> résumé FR          -> delivery/resume_fr.md
    3. Étape « action_points » -> points d'action FR -> delivery/points_action_fr.md
    4. Étape « translation »   -> traductions EN     -> delivery/summary_en.md
                                                        delivery/action_items_en.md

Le raisonnement (résumé / extraction / traduction) est réalisé par le LLM
piloté par l'agent. Ce script ne fait qu'orchestrer les outils ; c'est l'agent
qui décide quand les appeler. Les consignes de chaque étape vivent dans prompts/.

Utilisation :
    python agent_workflow.py                      # transcript_fr.txt par défaut
    python agent_workflow.py chemin/vers/transcript.txt

Le backend du modèle est choisi automatiquement selon les variables
d'environnement disponibles (voir build_model()).
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# Charge les variables définies dans le fichier .env (clés API, modèle, etc.).
load_dotenv()

from smolagents import (
    CodeAgent,
    InferenceClientModel,
    LiteLLMModel,
    OpenAIServerModel,
    tool,
)

# Dossier contenant les prompts détaillés par étape (résolu par rapport au
# fichier source, pour fonctionner quel que soit le dossier d'exécution).
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

# --------------------------------------------------------------------------- #
# Outils mis à la disposition de l'agent
# --------------------------------------------------------------------------- #


@tool
def load_prompt(step: str) -> str:
    """Charge les instructions détaillées d'une étape du workflow.

    Args:
        step: Nom de l'étape ('summary', 'action_points' ou 'translation').
    """
    path = os.path.join(PROMPTS_DIR, f"{step}.md")
    if not os.path.exists(path):
        available = [f[:-3] for f in os.listdir(PROMPTS_DIR) if f.endswith(".md")]
        raise FileNotFoundError(
            f"Étape inconnue : '{step}'. Étapes disponibles : {available}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@tool
def read_transcript(path: str) -> str:
    """Lit le contenu d'un fichier transcript et le renvoie sous forme de texte.

    Args:
        path: Chemin vers le fichier transcript à lire.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@tool
def write_file(path: str, content: str) -> str:
    """Écrit un fichier Markdown sur le disque (crée le dossier parent au besoin).

    Args:
        path: Chemin du fichier de sortie à créer ou écraser.
        content: Contenu Markdown à sauvegarder.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Fichier écrit : {path} ({len(content)} caractères)."


# --------------------------------------------------------------------------- #
# Sélection du backend LLM
# --------------------------------------------------------------------------- #


def build_model(openai_extra: dict | None = None):
    """Construit un modèle smolagents à partir des variables d'environnement.

    Ordre de préférence :
        1. OPENAI_API_KEY        -> OpenAIServerModel (OPENAI_MODEL, def. gpt-5.6-terra)
        2. HF_TOKEN / HF_API_KEY -> InferenceClientModel (HF_MODEL, def. Qwen2.5-Coder)
        3. LITELLM_MODEL         -> LiteLLMModel (ex. anthropic/claude-sonnet-4-6)

    Args:
        openai_extra: paramètres de génération additionnels transmis uniquement
            au backend OpenAI (ex. {"reasoning_effort": "none"} requis par
            gpt-5.6-terra en mode tool-calling sur /v1/chat/completions).

    Lève une RuntimeError explicite si aucune clé n'est disponible.
    """
    if os.getenv("OPENAI_API_KEY"):
        model_id = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
        print(f"[model] OpenAIServerModel : {model_id}")
        return OpenAIServerModel(model_id=model_id, **(openai_extra or {}))

    if os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY"):
        model_id = os.getenv("HF_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
        print(f"[model] InferenceClientModel : {model_id}")
        return InferenceClientModel(
            model_id=model_id,
            token=os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY"),
        )

    if os.getenv("LITELLM_MODEL"):
        model_id = os.environ["LITELLM_MODEL"]
        print(f"[model] LiteLLMModel : {model_id}")
        return LiteLLMModel(model_id=model_id)

    raise RuntimeError(
        "Aucun backend LLM configuré. Définissez l'une de ces variables "
        "d'environnement :\n"
        "  - OPENAI_API_KEY (+ OPENAI_MODEL optionnel)\n"
        "  - HF_TOKEN       (+ HF_MODEL optionnel)\n"
        "  - LITELLM_MODEL  (ex. 'anthropic/claude-sonnet-4-6' + clé du provider)\n"
    )


# --------------------------------------------------------------------------- #
# Construction de l'agent et de la tâche
# --------------------------------------------------------------------------- #

# Les quatre livrables attendus (noms de fichiers dans le dossier de sortie).
DELIVERABLES = [
    "resume_fr.md",
    "points_action_fr.md",
    "summary_en.md",
    "action_items_en.md",
]

TASK_TEMPLATE = """\
Tu es un assistant qui traite le compte rendu d'une réunion.

La langue initiale du transcript est le FRANÇAIS.

IMPORTANT :
- Tu disposes RÉELLEMENT des outils `read_transcript`, `load_prompt` et
  `write_file` : les fichiers EXISTENT et sont accessibles via ces outils. Ne
  refuse jamais la tâche et n'affirme jamais que tu ne peux pas y accéder.
- Pour CHAQUE étape, commence par charger ses instructions détaillées avec
  `load_prompt(<nom_étape>)`, puis applique-les scrupuleusement.
- Réponds TOUJOURS avec un bloc de code Python ; n'écris jamais une réponse en
  texte seul tant que la tâche n'est pas terminée.

Déroulé du workflow :

0. Lis le transcript : `read_transcript("{transcript_path}")`.

1. ÉTAPE « summary » :
   - charge ses consignes : `load_prompt("summary")` ;
   - rédige le résumé en français en suivant ces consignes ;
   - écris-le : `write_file("{output_dir}/resume_fr.md", <résumé_fr>)`.

2. ÉTAPE « action_points » :
   - charge ses consignes : `load_prompt("action_points")` ;
   - extrais les points d'action en français en suivant ces consignes ;
   - écris-les : `write_file("{output_dir}/points_action_fr.md", <actions_fr>)`.

3. ÉTAPE « translation » :
   - charge ses consignes : `load_prompt("translation")` ;
   - traduis en anglais le résumé ET les points d'action en suivant ces consignes ;
   - écris : `write_file("{output_dir}/summary_en.md", <résumé_en>)` ;
   - écris : `write_file("{output_dir}/action_items_en.md", <actions_en>)`.

4. Donne comme réponse finale la liste des quatre fichiers écrits.

N'invente aucune information qui ne figure pas dans le transcript.
"""


def build_agent(model) -> CodeAgent:
    """Crée le CodeAgent avec les outils nécessaires au workflow."""
    return CodeAgent(
        tools=[load_prompt, read_transcript, write_file],
        model=model,
        max_steps=10,
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
        model = build_model()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    agent = build_agent(model)
    task = TASK_TEMPLATE.format(
        transcript_path=transcript_path, output_dir=output_dir
    )

    result = agent.run(task)

    print("\n" + "=" * 70)
    print("RAPPORT FINAL")
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
