import { googleAI } from "@genkit-ai/googleai";
import { genkit } from "genkit";
import { dirname } from "path";
import { fileURLToPath } from "url";

export const ai = genkit({
  plugins: [googleAI()],
  model: googleAI.model("gemini-1.5-pro-latest"),
  promptDir: dirname(fileURLToPath(import.meta.url)),
});

export { z } from "genkit";
