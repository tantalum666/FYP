import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import ts from "typescript";

// Test-only transpilation using the already installed compiler. No bundler/server.
export function resolve(specifier, context, next) {
  if (specifier.startsWith(".") && context.parentURL) {
    const base = new URL(specifier, context.parentURL);
    for (const extension of [".ts", ".tsx"]) {
      const candidate = new URL(base.href + extension);
      if (existsSync(candidate)) return next(candidate.href, context);
    }
  }
  return next(specifier, context);
}

export function load(url, context, next) {
  if (url.startsWith("file:") && /\.tsx?$/.test(url)) {
    return {
      format: "module",
      shortCircuit: true,
      source: ts.transpileModule(readFileSync(fileURLToPath(url), "utf8"), {
        compilerOptions: {
          module: ts.ModuleKind.ESNext,
          target: ts.ScriptTarget.ES2022,
          jsx: ts.JsxEmit.ReactJSX,
          verbatimModuleSyntax: true,
        },
      }).outputText,
    };
  }
  if (url.endsWith(".css"))
    return {
      format: "module",
      shortCircuit: true,
      source: "export default undefined;",
    };
  return next(url, context);
}
