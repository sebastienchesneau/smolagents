# CLAUDE.md — Projet agent smolagents (traitement de transcript)

Guide pour toute session Claude Code travaillant sur ce dépôt.

## Objectif du projet

Un agent construit avec **smolagents** (Hugging Face) qui, à partir d'un
transcript de réunion **en français**, produit quatre livrables :
résumé FR, points d'action FR, puis leurs traductions anglaises. Chaque livrable
est un **fichier Markdown distinct** dans `delivery/`.

## Architecture

- **`agent_workflow.py`** — point d'entrée unique. Contient :
  - 3 outils `@tool` : `load_prompt`, `read_transcript`, `write_file` ;
  - `build_model()` — choisit le backend LLM selon les variables d'env ;
  - `TASK_TEMPLATE` — prompt maître qui orchestre le workflow par étapes ;
  - `DELIVERABLES` — les 4 fichiers attendus, vérifiés en fin de `main()` ;
  - `build_agent()` / `main()`.
- **`prompts/`** — un prompt détaillé **par étape**, chargé à l'exécution par
  l'outil `load_prompt("<étape>")` :
  - `summary.md` → résumé FR → `delivery/resume_fr.md`
  - `action_points.md` → points d'action FR → `delivery/points_action_fr.md`
  - `translation.md` → traductions EN → `delivery/summary_en.md` + `delivery/action_items_en.md`
- **`transcript_fr.txt`** — transcript d'exemple (réunion « Portail Client v2 »).
- **`delivery/`** — sortie générée (les 4 `.md`).
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

```bash
cd /home/sebastien.chesneau/workspace_test/smolagents
python3 agent_workflow.py                 # transcript_fr.txt -> delivery/
python3 agent_workflow.py autre.txt       # autre transcript
OUTPUT_DIR=livrables python3 agent_workflow.py
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
