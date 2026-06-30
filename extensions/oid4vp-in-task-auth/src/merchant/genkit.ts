import { genkit } from "genkit";
import { openAI } from "@genkit-ai/compat-oai/openai";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Default chat model. `gpt-4o-mini` is inexpensive and reliably produces the structured JSON the
 * merchant's request parser depends on. Override with the `OPENAI_MODEL` environment variable.
 */
const DEFAULT_MODEL = 'gpt-4o-mini'

const importMetaUrl = import.meta.url

export const ai = genkit({
    plugins: [openAI()],
    model: openAI.model(process.env.OPENAI_MODEL || DEFAULT_MODEL),
    promptDir: dirname(fileURLToPath(importMetaUrl)),
})
