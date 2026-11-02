#!/usr/bin/env python3
"""Socle commun aux variantes d'agent (`agent_workflow.py`, `agent_workflow2.py`).

Regroupe les éléments partagés par toutes les variantes :
- les outils `@tool` : `load_prompt`, `read_transcript`, `write_file` ;
- `build_model()` : sélection du backend LLM selon les variables d'environnement ;
- `DELIVERABLES` : les quatre fichiers de sortie attendus.

Les variantes importent depuis ce module :
    from base import DELIVERABLES, build_model, load_prompt, read_transcript, write_file
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

# Charge les variables définies dans le fichier .env (clés API, modèle, etc.).
load_dotenv()

from smolagents import (
    InferenceClientModel,
    LiteLLMModel,
    OpenAIServerModel,
    tool,
)

# Dossier contenant les prompts détaillés par étape (résolu par rapport au
# fichier source, pour fonctionner quel que soit le dossier d'exécution).
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

# Les quatre livrables attendus (noms de fichiers dans le dossier de sortie).
DELIVERABLES = [
    "resume_fr.md",
    "points_action_fr.md",
    "summary_en.md",
    "action_items_en.md",
]

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
# Boucle d'exécution partagée par toutes les variantes d'agent
# --------------------------------------------------------------------------- #


def run_workflow(
    agent_factory, task_template, *, label, default_output_dir, openai_extra=None
) -> int:
    """Exécute le workflow commun à toutes les variantes d'agent.

    Gère : résolution des chemins, construction du modèle, lancement de l'agent,
    puis vérification que les quatre livrables ont bien été écrits.

    Args:
        agent_factory: fonction `model -> agent` (c'est ce qui change entre les
            variantes : CodeAgent vs ToolCallingAgent vs multi-agent).
        task_template: le prompt de la tâche, avec les champs `{transcript_path}`
            et `{output_dir}` à formater.
        label: nom de la variante, affiché dans l'en-tête du rapport.
        default_output_dir: dossier de sortie propre à la variante (chaque
            variante a le sien). Surchargé par la variable d'env OUTPUT_DIR.
        openai_extra: paramètres de génération additionnels pour le backend
            OpenAI (ex. {"reasoning_effort": "none"}).

    Codes de retour : 0 OK · 1 transcript introuvable · 2 pas de backend LLM ·
    3 livrables manquants.
    """
    transcript_path = os.path.abspath(
        sys.argv[1] if len(sys.argv) > 1 else "transcript_fr.txt"
    )
    output_dir = os.path.abspath(os.getenv("OUTPUT_DIR", default_output_dir))

    if not os.path.exists(transcript_path):
        print(f"Transcript introuvable : {transcript_path}", file=sys.stderr)
        return 1

    try:
        model = build_model(openai_extra=openai_extra)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # Nettoie les livrables d'un run précédent : la vérification finale teste
    # l'existence des fichiers ; sans ce nettoyage, un fichier périmé masquerait
    # un échec de ce run (ex. un sous-agent qui n'écrit pas sa sortie).
    os.makedirs(output_dir, exist_ok=True)
    for name in DELIVERABLES:
        stale = os.path.join(output_dir, name)
        if os.path.exists(stale):
            os.remove(stale)

    agent = agent_factory(model)
    task = task_template.format(
        transcript_path=transcript_path, output_dir=output_dir
    )

    # Chronométrage du cycle (de la mise en route de l'agent à la fin).
    start_dt = datetime.now()
    start_perf = time.perf_counter()
    print(f"[timing] Début : {start_dt:%Y-%m-%d %H:%M:%S}")

    result = agent.run(task)

    elapsed = time.perf_counter() - start_perf
    end_dt = datetime.now()
    print(
        f"[timing] Fin : {end_dt:%Y-%m-%d %H:%M:%S} "
        f"— durée du cycle : {elapsed:.1f} s"
    )

    print("\n" + "=" * 70)
    print(f"RAPPORT FINAL ({label})")
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
