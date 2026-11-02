# Agent smolagents — Traitement de transcript de réunion

Un agent construit avec [**smolagents**](https://github.com/huggingface/smolagents)
(Hugging Face) qui, à partir d'un transcript de réunion **en français**, déroule
le workflow suivant :

1. **Lire** le transcript ;
2. **Résumer** la réunion (en français) ;
3. **Extraire les points d'action** (en français), avec responsable et échéance
   quand c'est possible ;
4. **Traduire en anglais** le résumé *et* les points d'action ;
5. **Sauvegarder** le tout dans un rapport Markdown (`rapport_reunion.md`).

> Note : « GitFace » = Hugging Face. `smolagents` est la librairie d'agents de
> Hugging Face.

## Fichiers

| Fichier | Rôle |
|---|---|
| `base.py` | **Socle commun** : outils (`load_prompt`, `read_transcript`, `write_file`), `build_model`, `DELIVERABLES`. Importé par les deux variantes. |
| `agent_workflow.py` | Variante 1 — agent **`CodeAgent`** (l'agent écrit du code Python). **Fichier principal.** |
| `agent_workflow2.py` | Variante 2 — agent **`ToolCallingAgent`** (paradigme agentique *tool-calling* : appels d'outils JSON). |
| `agent_workflow3.py` | Variante 3 — **multi-agent** : un manager délègue à `summarizer`, `action_extractor`, `translator`. |
| `prompts/` | Un prompt détaillé par étape, chargé à l'exécution : `summary.md`, `action_points.md`, `translation.md`. |
| `transcript_fr.txt` | Transcript d'exemple (réunion de lancement, en français). |
| `delivery/` | Livrables, **un sous-dossier par variante** (`v1_codeagent/`, `v2_toolcalling/`, `v3_multiagent/`), 4 fichiers chacun. |
| `requirements.txt` | Dépendances. |

## Installation

```bash
pip install -r requirements.txt
```

## Exécution avec un vrai LLM

L'agent choisit son backend selon les variables d'environnement présentes :

```bash
# Option A — OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-5.6-terra"      # optionnel

# Option B — Hugging Face Inference
export HF_TOKEN="hf_..."
export HF_MODEL="Qwen/Qwen2.5-Coder-32B-Instruct"   # optionnel

# Option C — LiteLLM (Anthropic, Mistral, etc.)
export LITELLM_MODEL="anthropic/claude-sonnet-4-6"
export ANTHROPIC_API_KEY="sk-ant-..."

python agent_workflow.py                 # variante 1 (CodeAgent)
python agent_workflow.py mon_transcript.txt
python agent_workflow2.py                # variante 2 (ToolCallingAgent)
python agent_workflow3.py                # variante 3 (multi-agent)
```

### Trois variantes d'agent

| | `agent_workflow.py` | `agent_workflow2.py` | `agent_workflow3.py` |
|---|---|---|---|
| Classe | `CodeAgent` | `ToolCallingAgent` | manager `CodeAgent` + 3 sous-agents |
| Paradigme | l'agent **écrit du code Python** qui appelle les outils | l'agent **appelle les outils** via des appels de fonction (JSON) | un **manager délègue** à des agents spécialisés (`managed_agents`) |
| Outils / prompts / livrables | — | identiques | identiques (tout vient de `base.py`) |
| Dossier de sortie | `delivery/v1_codeagent/` | `delivery/v2_toolcalling/` | `delivery/v3_multiagent/` |

Les trois variantes réutilisent le socle commun `base.py` (outils, `build_model`,
`run_workflow`, `DELIVERABLES`). **Chaque variante écrit dans son propre dossier**
sous `delivery/` (surchargeable via `OUTPUT_DIR`).

> Note `gpt-5.6-terra` : en mode tool-calling sur `/v1/chat/completions`, l'API
> exige `reasoning_effort='none'` — `agent_workflow2.py` le passe automatiquement
> au modèle.

Chaque variante écrit **quatre fichiers distincts** dans son propre dossier
(`delivery/v1_codeagent/`, `delivery/v2_toolcalling/` ou `delivery/v3_multiagent/`) :

| Fichier | Contenu |
|---|---|
| `resume_fr.md` | Résumé de la réunion (français) |
| `points_action_fr.md` | Points d'action (français) |
| `summary_en.md` | Résumé (anglais) |
| `action_items_en.md` | Points d'action (anglais) |

Le dossier de sortie de chaque variante est surchargeable via `OUTPUT_DIR`.

## Comment ça marche

- Trois outils (`@tool`) sont fournis à l'agent : `load_prompt`,
  `read_transcript` et `write_file`.
- Le **raisonnement** (résumé, extraction, traduction) est réalisé par le LLM
  piloté par l'agent ; le script ne fait qu'orchestrer.
- Le workflow est **découpé en étapes**, chacune avec son prompt détaillé dans
  `prompts/`. À chaque étape, l'agent appelle `load_prompt("<étape>")` pour
  charger ses consignes, puis les applique :

  (`<sortie>` = le dossier propre à la variante lancée)

  | Étape | Prompt chargé | Fichier produit |
  |---|---|---|
  | `summary` | `prompts/summary.md` | `<sortie>/resume_fr.md` |
  | `action_points` | `prompts/action_points.md` | `<sortie>/points_action_fr.md` |
  | `translation` | `prompts/translation.md` | `<sortie>/summary_en.md` + `<sortie>/action_items_en.md` |

- Pour **ajuster le comportement d'une étape**, il suffit d'éditer son fichier
  dans `prompts/` — pas besoin de toucher au code Python.
