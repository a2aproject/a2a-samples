import { googleAI } from "@genkit-ai/googleai";
import { genkit } from "genkit";
import { dirname } from "path";
import { fileURLToPath } from "url";

export const ai = genkit({
  plugins: [googleAI()],
  model: googleAI.model("gemini-2.5-flash-preview-05-20"),
  promptDir: dirname(fileURLToPath(import.meta.url)),
});

export { z } from "genkit";