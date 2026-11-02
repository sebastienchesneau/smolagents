#!/usr/bin/env python3
import sys
from smolagents import ToolCallingAgent, tool
from base import build_model
import os
import shutil
# Tâche : un ToolCallingAgent n'exécute PAS de code, il ne peut qu'appeler des
# outils (en JSON). Il faut donc lui fournir un outil pour chaque action réelle.
DEFAULT_TASK = (
    "Calcule la somme des 15 premiers termes de la suite de Fibonacci "
    "(fibonacci(0)=0, fibonacci(1)=1), puis copie le fichier "
    "/home/sebastien.chesneau/workspace_test/smolagents/transcript_fr.txt dans le dossier "
    "/home/sebastien.chesneau/workspace_test/smolagents/delivery/toolagenttest"
)


@tool
def copy_file(src: str, dst_dir: str) -> str:
    """Copie un fichier dans un dossier (créé si besoin).

    Args:
        src: Chemin du fichier source.
        dst_dir: Dossier de destination.
    """


    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(src))
    shutil.copy(src, dst)
    return f"Copié vers {dst}"


def main() -> int:
    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK

    # gpt-5.6-terra refuse les function tools quand reasoning_effort est actif
    # sur /v1/chat/completions -> on le force à 'none'.
    # tools : un ToolCallingAgent n'a de capacités QUE via ses outils.
    agent = ToolCallingAgent(
        tools=[copy_file],
        model=build_model(openai_extra={"reasoning_effort": "none"}),
        max_steps=12,
    )

    result = agent.run(task)
    print(f"\nRéponse : {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
