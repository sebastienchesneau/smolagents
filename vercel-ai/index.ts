/**
 * Variante Vercel AI SDK (TypeScript) — équivalent de agent_workflow2.py.
 *
 * Même workflow (transcript FR -> résumé FR, points d'action FR, traductions EN)
 * et mêmes quatre livrables que les variantes Python, livrés dans delivery/.
 *
 * PARADIGME : tool-calling. `generateText` boucle automatiquement tant que le
 * modèle appelle des outils (`stopWhen: stepCountIs(...)` = le garde-fou de
 * boucle, équivalent de max_steps / recursion_limit).
 *
 * On réutilise les MÊMES prompts/ et transcript_fr.txt que le projet Python
 * (dossier parent), et le même .env (OPENAI_API_KEY + OPENAI_MODEL).
 *
 *   npm start                      # transcript_fr.txt par défaut
 *   npm start -- ../autre.txt      # autre transcript
 */

import { createOpenAI } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool } from "ai";
import { config } from "dotenv";
import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

// --- Chemins : le repo Python est le dossier PARENT de vercel-ai/ ----------
const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..");
const PROMPTS_DIR = join(REPO, "prompts");
const DELIVERABLES = [
  "resume_fr.md",
  "points_action_fr.md",
  "summary_en.md",
  "action_items_en.md",
];

// Charge le .env du projet Python (clé API + modèle).
config({ path: join(REPO, ".env") });

// --- Outils (mêmes 3 outils que base_tools.py) -----------------------------
const load_prompt = tool({
  description:
    "Charge les instructions détaillées d'une étape du workflow ('summary', 'action_points' ou 'translation').",
  inputSchema: z.object({ step: z.string() }),
  execute: async ({ step }) => {
    const p = join(PROMPTS_DIR, `${step}.md`);
    if (!existsSync(p)) {
      const avail = readdirSync(PROMPTS_DIR)
        .filter((f) => f.endsWith(".md"))
        .map((f) => f.slice(0, -3));
      throw new Error(`Étape inconnue : '${step}'. Disponibles : ${avail}`);
    }
    return readFileSync(p, "utf-8");
  },
});

const read_transcript = tool({
  description: "Lit le contenu d'un fichier transcript et le renvoie en texte.",
  inputSchema: z.object({ path: z.string() }),
  execute: async ({ path }) => readFileSync(path, "utf-8"),
});

const write_file = tool({
  description:
    "Écrit un fichier Markdown sur le disque (crée le dossier parent au besoin).",
  inputSchema: z.object({ path: z.string(), content: z.string() }),
  execute: async ({ path, content }) => {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, content, "utf-8");
    return `Fichier écrit : ${path} (${content.length} caractères).`;
  },
});

// --- Tâche (même déroulé que agent_workflow2.py / base_tools.py) -----------
function buildTask(transcriptPath: string, outputDir: string): string {
  return `Tu es un assistant qui traite le compte rendu d'une réunion.

La langue initiale du transcript est le FRANÇAIS.

IMPORTANT :
- Tu disposes RÉELLEMENT des outils read_transcript, load_prompt et write_file.
  Ne refuse jamais la tâche et n'affirme jamais que tu ne peux pas y accéder.
- Avance en APPELANT les outils. Pour chaque étape, charge d'abord ses consignes
  avec load_prompt, puis applique-les.
- Le contenu rédigé doit être passé en argument content de write_file.

Déroulé du workflow :

0. Appelle read_transcript avec path="${transcriptPath}".

1. ÉTAPE « summary » :
   - load_prompt avec step="summary" ;
   - rédige le résumé en français ;
   - write_file avec path="${outputDir}/resume_fr.md".

2. ÉTAPE « action_points » :
   - load_prompt avec step="action_points" ;
   - extrais les points d'action en français ;
   - write_file avec path="${outputDir}/points_action_fr.md".

3. ÉTAPE « translation » :
   - load_prompt avec step="translation" ;
   - traduis en anglais le résumé ET les points d'action ;
   - write_file avec path="${outputDir}/summary_en.md" (résumé EN) ;
   - write_file avec path="${outputDir}/action_items_en.md" (actions EN).

4. Quand les quatre fichiers sont écrits, donne la liste des fichiers produits.

N'invente aucune information qui ne figure pas dans le transcript.`;
}

async function main(): Promise<number> {
  const transcriptPath = process.argv[2]
    ? join(process.cwd(), process.argv[2])
    : join(REPO, "transcript_fr.txt");
  const outputDir = process.env.OUTPUT_DIR
    ? join(process.cwd(), process.env.OUTPUT_DIR)
    : join(REPO, "delivery", "v8_vercel_ai");

  if (!existsSync(transcriptPath)) {
    console.error(`Transcript introuvable : ${transcriptPath}`);
    return 1;
  }
  if (!process.env.OPENAI_API_KEY) {
    console.error("Aucun backend LLM configuré : OPENAI_API_KEY manquant dans .env.");
    return 2;
  }

  // Nettoie les livrables d'un run précédent.
  mkdirSync(outputDir, { recursive: true });
  for (const name of DELIVERABLES) {
    const stale = join(outputDir, name);
    if (existsSync(stale)) rmSync(stale);
  }

  const openai = createOpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    baseURL: process.env.OPENAI_BASE_URL, // undefined -> endpoint OpenAI par défaut
  });
  const modelId = process.env.OPENAI_MODEL ?? "gpt-5.6-terra";
  console.log(`[model] Vercel AI SDK (chat) : ${modelId}`);

  console.log("=".repeat(70));
  console.log("Variante : Vercel AI SDK (generateText)");
  console.log(`Transcript : ${transcriptPath}`);
  console.log(`Sortie     : ${outputDir}`);
  console.log("=".repeat(70));

  const start = Date.now();

  const { text, steps } = await generateText({
    model: openai.chat(modelId), // chat/completions, comme les variantes Python
    system: "Réponds en français. Avance en appelant les outils fournis.",
    tools: { load_prompt, read_transcript, write_file },
    stopWhen: stepCountIs(12), // garde-fou de boucle (= max_steps)
    // gpt-5.6-terra exige reasoning_effort='none' avec des function tools.
    providerOptions: { openai: { reasoningEffort: "none" } },
    prompt: buildTask(transcriptPath, outputDir),
  });

  const elapsed = ((Date.now() - start) / 1000).toFixed(1);
  console.log(`[timing] Durée : ${elapsed} s (${steps.length} étapes)`);
  console.log(`\nRéponse de l'agent :\n${text}\n`);

  const missing = DELIVERABLES.filter(
    (name) => !existsSync(join(outputDir, name))
  );
  if (missing.length) {
    console.error(`ÉCHEC : fichiers manquants : ${missing}`);
    return 3;
  }

  console.log("OK : les quatre livrables ont été écrits :");
  for (const name of DELIVERABLES) console.log(`  - ${join(outputDir, name)}`);
  return 0;
}

main().then((code) => process.exit(code));
