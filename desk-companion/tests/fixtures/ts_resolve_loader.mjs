/** Resolve extensionless TypeScript imports so a Node check can load production modules. */

export async function resolve(specifier, context, nextResolve) {
  if (
    (specifier.startsWith("./") || specifier.startsWith("../")) &&
    !/\.(tsx?|jsx?|mjs|cjs|json)$/.test(specifier)
  ) {
    let last;
    for (const ext of [".ts", ".tsx", ".js", ".mjs"]) {
      try {
        return await nextResolve(specifier + ext, context);
      } catch (error) {
        last = error;
      }
    }
    throw last;
  }
  return nextResolve(specifier, context);
}
