#!/usr/bin/env python3
"""Socle NEUTRE (sans framework) partagé par les variantes LlamaIndex et LangGraph.

Contient ce qui ne dépend d'aucun framework d'agent :
- les trois outils en fonctions Python natives (load_prompt, read_transcript,
  write_file) — chaque framework les enveloppe à sa façon ;
- `TASK_TEMPLATE` : le déroulé du workflow (identique à agent_workflow2.py) ;
- `resolve_io` / `verify_deliverables` : la logique de chemins et la vérification
  finale des quatre livrables, communes à toutes les variantes.

Réutilise `PROMPTS_DIR` et `DELIVERABLES` de `base.py` (source de vérité unique).
"""

from __future__ import annotations

import os
import sys

from base import DELIVERABLES, PROMPTS_DIR  # noqa: F401 (DELIVERABLES ré-exporté)

# --------------------------------------------------------------------------- #
# Outils (fonctions Python natives)
# --------------------------------------------------------------------------- #


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


def read_transcript(path: str) -> str:
    """Lit le contenu d'un fichier transcript et le renvoie sous forme de texte.

    Args:
        path: Chemin vers le fichier transcript à lire.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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
# Tâche commune (même déroulé que agent_workflow2.py)
# --------------------------------------------------------------------------- #

TASK_TEMPLATE = """\
Tu es un assistant qui traite le compte rendu d'une réunion.

La langue initiale du transcript est le FRANÇAIS.

IMPORTANT :
- Tu disposes RÉELLEMENT des outils `read_transcript`, `load_prompt` et
  `write_file` : les fichiers EXISTENT et sont accessibles via ces outils. Ne
  refuse jamais la tâche et n'affirme jamais que tu ne peux pas y accéder.
- Avance en APPELANT les outils. Pour chaque étape, charge d'abord ses consignes
  détaillées avec `load_prompt`, puis applique-les.
- Le contenu rédigé (résumé, points d'action, traductions) doit être passé en
  argument `content` de `write_file`.

Déroulé du workflow :

0. Appelle `read_transcript` avec path="{transcript_path}".

1. ÉTAPE « summary » :
   - appelle `load_prompt` avec step="summary" ;
   - rédige le résumé en français selon ces consignes ;
   - appelle `write_file` avec path="{output_dir}/resume_fr.md" et le résumé.

2. ÉTAPE « action_points » :
   - appelle `load_prompt` avec step="action_points" ;
   - extrais les points d'action en français selon ces consignes ;
   - appelle `write_file` avec path="{output_dir}/points_action_fr.md".

3. ÉTAPE « translation » :
   - appelle `load_prompt` avec step="translation" ;
   - traduis en anglais le résumé ET les points d'action selon ces consignes ;
   - appelle `write_file` avec path="{output_dir}/summary_en.md" (résumé EN) ;
   - appelle `write_file` avec path="{output_dir}/action_items_en.md" (actions EN).

4. Quand les quatre fichiers sont écrits, donne la liste des fichiers produits.

N'invente aucune information qui ne figure pas dans le transcript.
"""

# --------------------------------------------------------------------------- #
# Chemins + vérification des livrables (communs à toutes les variantes)
# --------------------------------------------------------------------------- #


def resolve_io(default_output_dir: str):
    """Résout le transcript et le dossier de sortie, et nettoie les livrables périmés.

    Returns:
        (transcript_path, output_dir), ou (None, None) si le transcript est
        introuvable (l'appelant renverra alors le code de sortie 1).
    """
    transcript_path = os.path.abspath(
        sys.argv[1] if len(sys.argv) > 1 else "transcript_fr.txt"
    )
    output_dir = os.path.abspath(os.getenv("OUTPUT_DIR", default_output_dir))

    if not os.path.exists(transcript_path):
        print(f"Transcript introuvable : {transcript_path}", file=sys.stderr)
        return None, None

    # Nettoie les livrables d'un run précédent (sinon un fichier périmé masquerait
    # un échec de ce run).
    os.makedirs(output_dir, exist_ok=True)
    for name in DELIVERABLES:
        stale = os.path.join(output_dir, name)
        if os.path.exists(stale):
            os.remove(stale)

    return transcript_path, output_dir


def verify_deliverables(output_dir: str) -> list[str]:
    """Retourne la liste des livrables manquants dans `output_dir` (vide si OK)."""
    return [
        name for name in DELIVERABLES
        if not os.path.exists(os.path.join(output_dir, name))
    ]
