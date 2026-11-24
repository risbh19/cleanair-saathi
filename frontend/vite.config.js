import { defineConfig } from "vite";

import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

export default defineConfig({
  plugins: [{
    name: "saathi-shell",
    enforce: "post",
    generateBundle(_, bundle) {
      const assets = ["/index.html", "/manifest.webmanifest", "/saathi.svg",
        ...Object.keys(bundle).filter(path => path.startsWith("assets/")).map(path => "/" + path)];
      const version = createHash("sha256").update(assets.join("|")).digest("hex").slice(0, 16);
      const template = readFileSync(new URL("./sw-template.js", import.meta.url), "utf8");
      this.emitFile({ type: "asset", fileName: "sw.js", source: template
        .replace("__SAATHI_ASSETS__", JSON.stringify(assets))
        .replace("__SAATHI_CACHE__", JSON.stringify("saathi-shell-" + version)) });
    },
  }],
  server: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", rewrite: (p) => p.slice(4) },
    },
  },
});
