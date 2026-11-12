# CLAUDE.md — Projet agent smolagents (traitement de transcript)

Guide pour toute session Claude Code travaillant sur ce dépôt.

## Objectif du projet

Un agent construit avec **smolagents** (Hugging Face) qui, à partir d'un
transcript de réunion **en français**, produit quatre livrables :
résumé FR, points d'action FR, puis leurs traductions anglaises. Chaque livrable
est un **fichier Markdown distinct**, écrit dans le dossier propre à la variante.

## Organisation du dépôt (par techno)

Les scripts sont regroupés **par techno** dans un sous-dossier ; l'infra
**partagée** reste à la racine :

```
.                      ← lancer les scripts depuis ICI (racine du dépôt)
├── base.py            socle smolagents (partagé)
├── base_tools.py      outils + helpers communs (langgraph & llamaindex)
├── prompts/  transcript_fr.txt  delivery/  .env   infra partagée
├── smolagents/        agent_workflow{,2,3}.py + agent_test*.py
├── llamaindex/        base_llamaindex.py + agent_llamaindex{,_react,_workflow}.py
├── langgraph/         agent_langgraph{,_explicit,_workflow}.py
└── vercel-ai/         variante Vercel AI SDK
```

Chaque script déplacé en sous-dossier commence par un **bootstrap `sys.path`**
(ajoute la racine au path) pour que `from base ...` / `from base_tools ...`
restent résolus. **Toujours lancer depuis la racine** (`python3 smolagents/…`) :
`base_tools.resolve_io` résout `transcript_fr.txt` et `delivery/` par rapport au
répertoire courant.

## Architecture (socle smolagents)

- **`base.py`** — socle commun aux variantes smolagents :
  - 3 outils `@tool` : `load_prompt`, `read_transcript`, `write_file` ;
  - `build_model(openai_extra=None)` — choisit le backend LLM selon l'env ;
  - `DELIVERABLES` — les 4 fichiers attendus ;
  - `run_workflow(agent_factory, task_template, *, label, default_output_dir,
    openai_extra=None)` — boucle commune : chemins, modèle, `agent.run`, puis
    vérification des 4 livrables.
- **Trois variantes** (chacune = prompt + `build_agent` + `main`, tout le reste
  vient de `base.py`) :
  - `smolagents/agent_workflow.py` — `CodeAgent` (le LLM écrit du code) → `delivery/v1_codeagent/`
  - `smolagents/agent_workflow2.py` — `ToolCallingAgent` (appels d'outils JSON) → `delivery/v2_toolcalling/`
  - `smolagents/agent_workflow3.py` — **multi-agent** : manager + `summarizer` /
    `action_extractor` / `translator` (`managed_agents`) → `delivery/v3_multiagent/`
- **`prompts/`** — un prompt détaillé **par étape**, chargé à l'exécution par
  l'outil `load_prompt("<étape>")` : `summary.md`, `action_points.md`,
  `translation.md`.
- **`transcript_fr.txt`** — transcript d'exemple (réunion « Portail Client v2 »).
- **`delivery/`** — sorties générées, **un sous-dossier par variante**.
- **`.env`** — `OPENAI_API_KEY` + `OPENAI_MODEL` (ignoré par git).

### Principe clé
Le script n'orchestre que les outils ; c'est le **LLM qui rédige** (résumé,
extraction, traduction). Pour **modifier le comportement d'une étape**, éditer
son fichier dans `prompts/` — **pas besoin de toucher au code Python**.

## Modèle LLM

- Backend par défaut : **OpenAI**, modèle **`gpt-5.6-terra`** (défini dans `.env`).
  - ⚠️ GPT-5.6 (famille Sol / Terra / Luna) est sorti en **juillet 2026**,
    après la date de connaissance par défaut — ce modèle existe bien, ID direct
    OpenAI : `gpt-5.6-terra`. Ne pas le « corriger » comme inexistant.
- `build_model()` sélectionne aussi, selon l'env : `HF_TOKEN` → HF Inference,
  `LITELLM_MODEL` → LiteLLM.

## Comment lancer

Toujours **depuis la racine du dépôt**, en préfixant par le dossier de la techno :

```bash
cd /home/sebastien.chesneau/workspace_test/smolagents
python3 smolagents/agent_workflow.py            # v1 CodeAgent    -> delivery/v1_codeagent/
python3 smolagents/agent_workflow2.py           # v2 ToolCalling  -> delivery/v2_toolcalling/
python3 smolagents/agent_workflow3.py           # v3 multi-agent  -> delivery/v3_multiagent/
python3 smolagents/agent_workflow.py autre.txt  # autre transcript
OUTPUT_DIR=livrables python3 smolagents/agent_workflow.py   # surcharge le dossier de sortie

python3 llamaindex/agent_llamaindex.py          # variantes LlamaIndex
python3 langgraph/agent_langgraph.py            # variantes LangGraph
```

Codes de sortie : `0` OK · `1` transcript introuvable · `2` aucun backend LLM
configuré · `3` le modèle n'a pas produit les 4 fichiers (→ relancer).

## Pièges connus

- **`gpt-5.6-terra` est un peu instable** sur ce workflow : il lui arrive de
  répondre en texte au lieu d'un bloc de code, voire de « refuser » en
  prétendant ne pas pouvoir accéder au fichier (→ `Error in code parsing`).
  Mitigations déjà en place : prompt durci (il DOIT toujours répondre en code et
  ne jamais refuser) + chemins absolus + vérification finale des 4 fichiers.
  Si un run échoue (`ÉCHEC : fichiers manquants`), **relancer** suffit souvent.
- Dépendances : `smolagents>=1.26`, `python-dotenv`, un client LLM (`openai`).

## Conventions

- Langue de travail et des réponses : **français** (accents corrects).
- Tout en UTF-8. Les livrables commencent par un titre Markdown `#`.
