import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";

async function sourceFiles(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map(async (entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(fullPath);
    if (/\.(ts|tsx|js|jsx)$/.test(entry.name) && !/\.(test|spec)\./.test(entry.name)) return [fullPath];
    return [];
  }));
  return nested.flat();
}

describe("architecture boundary", () => {
  it("prevents lib from importing modules through aliases or relative paths", async () => {
    const root = path.resolve(process.cwd(), "src/lib");
    const files = await sourceFiles(root);
    const violations: string[] = [];
    const forbidden = [
      /from\s+["']@\/modules\//,
      /import\s*\(\s*["']@\/modules\//,
      /from\s+["'](?:\.\.\/)+modules\//,
      /import\s*\(\s*["'](?:\.\.\/)+modules\//,
    ];

    for (const file of files) {
      const source = await readFile(file, "utf8");
      if (forbidden.some((pattern) => pattern.test(source))) violations.push(path.relative(process.cwd(), file));
    }

    expect(violations).toEqual([]);
  });
});
