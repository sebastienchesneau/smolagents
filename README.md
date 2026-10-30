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
| `agent_workflow.py` | L'agent (`CodeAgent`) + ses outils + la sélection du modèle. **C'est le fichier principal.** |
| `prompts/` | Un prompt détaillé par étape, chargé à l'exécution : `summary.md`, `action_points.md`, `translation.md`. |
| `transcript_fr.txt` | Transcript d'exemple (réunion de lancement, en français). |
| `delivery/` | Dossier des livrables : **un fichier par sortie** (voir ci-dessous). |
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

python agent_workflow.py                 # utilise transcript_fr.txt
python agent_workflow.py mon_transcript.txt
```

L'agent écrit **quatre fichiers distincts** dans `delivery/` :

| Fichier | Contenu |
|---|---|
| `resume_fr.md` | Résumé de la réunion (français) |
| `points_action_fr.md` | Points d'action (français) |
| `summary_en.md` | Résumé (anglais) |
| `action_items_en.md` | Points d'action (anglais) |

Le dossier de sortie est réglable via `OUTPUT_DIR` (défaut `delivery`).

## Comment ça marche

- Trois outils (`@tool`) sont fournis à l'agent : `load_prompt`,
  `read_transcript` et `write_file`.
- Le **raisonnement** (résumé, extraction, traduction) est réalisé par le LLM
  piloté par l'agent ; le script ne fait qu'orchestrer.
- Le workflow est **découpé en étapes**, chacune avec son prompt détaillé dans
  `prompts/`. À chaque étape, l'agent appelle `load_prompt("<étape>")` pour
  charger ses consignes, puis les applique :

  | Étape | Prompt chargé | Fichier produit |
  |---|---|---|
  | `summary` | `prompts/summary.md` | `delivery/resume_fr.md` |
  | `action_points` | `prompts/action_points.md` | `delivery/points_action_fr.md` |
  | `translation` | `prompts/translation.md` | `delivery/summary_en.md` + `delivery/action_items_en.md` |

- Pour **ajuster le comportement d'une étape**, il suffit d'éditer son fichier
  dans `prompts/` — pas besoin de toucher au code Python.
