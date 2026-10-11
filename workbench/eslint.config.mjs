import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";
import boundaries from "eslint-plugin-boundaries";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const compat = new FlatCompat({ baseDirectory: __dirname });

export default [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    files: ["src/lib/**/*.{js,jsx,ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", {
        patterns: [
          { group: ["@/modules/**", "../modules/**", "../../modules/**", "../../../modules/**", "../../../../modules/**"], message: "lib/ is infrastructure-only and must not import domain modules." }
        ]
      }]
    }
  },
  {
    files: ["src/**/*.{js,jsx,ts,tsx}"],
    plugins: { boundaries },
    settings: {
      "boundaries/elements": [
        { type: "app", pattern: "src/app/**" },
        { type: "module", pattern: "src/modules/*/**" },
        { type: "lib", pattern: "src/lib/**" },
        { type: "test", pattern: "**/*.{test,spec}.{js,jsx,ts,tsx}" }
      ]
    },
    rules: {
      "boundaries/element-types": ["error", {
        default: "disallow",
        rules: [
          { from: "app", allow: ["app", "module", "lib"] },
          { from: "module", allow: ["module", "lib"] },
          { from: "lib", allow: ["lib"] },
          { from: "test", allow: ["app", "module", "lib", "test"] }
        ]
      }]
    }
  }
];
