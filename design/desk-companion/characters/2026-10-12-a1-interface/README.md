# A1 interface artwork · 12 October 2026

Group 2. The user selected A1 and requested a persistent interactive page character. Two transparent native ImageGen edits were produced from the actually reviewed [T01 front reference](../2026-10-12-a1-turnaround-details/a1-t01-front.png), each in one call. The coordinator inspected both outputs. Original PNG bytes, exact prompts, input/native paths and hashes are preserved; no pixel postprocessing was applied.

| Asset | Current use | SHA-256 |
|---|---|---|
| [a1-idle-v1.png](a1-idle-v1.png) | Active intact open-eyed 2D illustration | `a7b428a2437da70880fea628dca23c0ded7a24294595b13437b4ae99fe5a09f9` |
| [a1-acknowledge-v1.png](a1-acknowledge-v1.png) | Historical only; user rejected the closed-eye click response; not shipped as a runtime frame | `fded6f6748626a0566e010728dece02614f294874383ebf62756cc2c1eddfdb0` |

Both PNGs are 1024×1536, RGBA, with more than 1.21 million fully transparent pixels. Native subject alpha is mostly 250–254, with faint low-alpha residue; this was preserved. [Manifest](manifest.json), [idle receipt](a1-idle-v1.receipt.json), [acknowledgement receipt](a1-acknowledge-v1.receipt.json) and [job record](generation-jobs.json) retain actual provenance and visual deviations. This is a native re-render from T01, not a pixel-identical extraction of the original concept.

Exact actual prompts: [idle](prompts/a1-idle-v1.txt) and [acknowledgement](prompts/a1-acknowledge-v1.txt). Two existing image workers were reused, their terminal results consumed and completion confirmed; no additional worker handles or retries were used. A Creative Production board was not mounted because only a nested board call was exposed and the skill prohibited that mounting route. No board completion is claimed.

The active runtime copy is byte-identical to the idle native output. The SVG viewport uses the `[282,13,460,1492]` view region to avoid transparent canvas margins. Only viewport cropping, uniform scaling and rigid whole-image feedback happen at render time; the PNG source remains unchanged. The latest [page interaction contract](../../../../desk-companion/docs/page-companion.md) supersedes closed-eye swapping, segmented SVG, deformed depth-mesh motion and the rejected 3D derivative.

A1 retains silver-gray long hair, gray-blue eyes, the physical-left open-ring clip and the original V4 clothing. The default outfit among nine variants has not been selected. The current page uses one complete image, with no joint slices, mesh deformation or perspective. Large waving/walking would need complete authored pose frames, which are not made. Original A1 3D geometry, rear construction, facial shapes, clothing binding and real voice/Pi validation remain unfinished. Old art, prompts, school originals and the licensed pixiv VRM remain preserved.
