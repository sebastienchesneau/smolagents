#!/usr/bin/env python3
import sys
from smolagents import CodeAgent
from base import build_model

# Tâche qui incite le LLM à écrire ses propres fonctions au runtime.
DEFAULT_TASK = (
    "Écris une fonction Python `fibonacci(n)` qui renvoie le n-ième terme de la "
    "suite de Fibonacci, puis utilise-la pour calculer la somme des 15 premiers "
    "termes. Renvoie cette somme. Puis une copie du fichier /home/sebastien.chesneau/workspace_test/smolagents/transcript_fr.txt dans le folder /home/sebastien.chesneau/workspace_test/smolagents/delivery/codeagenttest"
)

def main() -> int:
    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK

    # L'interpréteur du CodeAgent est restreint : par défaut il ne peut PAS
    # importer os/shutil. On les autorise pour qu'il puisse écrire lui-même
    # le code qui crée le dossier et copie le fichier.
    agent = CodeAgent(
        tools=[],
        model=build_model(),
        additional_authorized_imports=["os", "shutil"],
        verbosity_level=2,
    )

    result = agent.run(task)
    print(f"\nRéponse : {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
