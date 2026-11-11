# Revising existing scientific diagrams

Read this when updating a diagram rather than drawing a new one. Preserve the source's scientific meaning and caption, then improve the visual encoding. A change in color or geometry must not silently change what a mark represents.

## Decide what must remain true

Before editing, identify the dimensions, panel correspondence, units and the meaning of each arrow and colored region. For stateful processes, distinguish the input processed now, the state available now, the state saved afterward and the output used by the next step. For example, sampling a token does not mean its K/V have already been computed. Split a coarse operation into its real suboperations when that is the point readers need to understand; adding more decorative boxes does not accomplish this.

Comparison panels should use the same cell pitch and consistent symbols where equal geometry represents equal quantities. Distinguish visibility masks from measured weights and logical data structures from physical memory layouts. Record diagram-specific assumptions in the caption or accompanying source record; these examples are not universal requirements for every figure.

## Validate the actual renderer

Font-family lists do not guarantee that an export backend can find fallback glyphs. A rendered KV-cache example had missing circled digits, arrows and Greek characters even though ordinary Chinese and Latin text worked. Prefer native geometry for simple arrowheads and crosses. Give scientific glyphs an explicitly available font or use the formula-to-path route; retain the intended notation rather than silently dropping a symbol.

In that same CairoSVG run, `baseline-shift="sub"` did not give the expected subscript, and centered text with tspans produced inconsistent placement. When this occurs, position short subscripts explicitly with separate text nodes and smaller font sizes. Complex indices and equations are better handled by the formula tool. This is an observed backend issue, not a claim that all SVG viewers lack baseline-shift support.

Inspect the new export for missing glyphs, index placement, connector endpoints and clipping. A successful `inspect` reports structure, not typographic correctness. Examine a preview near the intended display width; a desktop preview of a multi-panel figure does not establish readability on a phone. For narrow layouts, split panels or provide an enlargement rather than merely shrinking labels.

## Stage replacement files and keep sources

The helpers deliberately refuse to overwrite output files. Generate edits and exports in a staging directory, inspect them, then replace the intended figure while preserving its established links. Do not delete the only source simply to make an output path available.

Keep the diagram component, equation fragment, generated TeX/formula SVG and relative-path composition JSON together when a formula is composed into a figure. Ordinary labels remain editable text; equation paths preserve appearance and must be regenerated from TeX for mathematical edits. Record the selected backend, output size and any confirmed local dependency setup alongside the figure. Avoid copying a machine-specific library path into a general installation requirement.
