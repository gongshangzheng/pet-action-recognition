# Scientific SVG and LaTeX

## Draw native SVG

Use an explicit `viewBox`, SVG namespace, and deliberate final physical dimensions. A useful single-column starting point is `width="89mm"` with a proportional height; verify the actual journal requirement. Set ordinary labels to a locally available font. Use `<g>` for meaningful objects, `<rect>`/`<path>` for geometry, `<marker>` for arrows, and `<title>`/`<desc>` for the figure's purpose. Maintain panel, method, and arrow styles consistently. Data plots should retain their plotting scripts and source data.

Keep visible labels as `<text>` where continued editing matters. Set `text-anchor` deliberately and use explicit coordinates; do not rely on HTML layout or unsupported `foreignObject`. Use presentation attributes or inline `style` with local `url(#id)` references. The helper rejects CSS `<style>` blocks so it can rename IDs without corrupting selectors. Export Matplotlib components with `svg.fonttype="none"` for editable ordinary text, then check installed fonts; this does not embed fonts or guarantee editable math. The helper accepts PNG/JPEG data-URI images but rejects external assets and executable or dynamic content. This is an authoring subset, not a sanitizer for hostile SVG.

## Select equation representation

Raw `$...$` inside SVG `<text>` is not LaTeX rendering. Choose a route explicitly:

- **Standalone SVG with stable glyphs:** compile LaTeX to DVI and use `dvisvgm --no-fonts` for vector glyph paths. This is the bundled formula route. Preserve TeX so equations remain reproducible and editable from source.
- **Simple expressions in Matplotlib:** MathText supports a subset of TeX syntax without a TeX install. Full `text.usetex=True` uses an installed TeX toolchain. Neither setting guarantees equation text remains editable in SVG.
- **Inkscape editing:** TexText can retain TeX source with an inserted equation. It is an optional GUI extension, not installed or tested by these scripts.
- **Document-owned typography:** Inkscape PDF+LaTeX export splits geometry into PDF and labels into `.pdf_tex`, letting the manuscript compile the math. This is a two-file LaTeX deliverable, not a standalone equation-bearing SVG. Select it only when requested and verify its LaTeX build.

For the bundled route, write only the math content, without `$` delimiters or a document wrapper, into `equation.txt`:

```tex
\mathcal{L}=\sum_{i=1}^{N}\lVert x_i-\hat{x}_i\rVert_2^2
```

Run `formula` as shown in SKILL.md. It saves both vector SVG and the complete `.tex` source, and rejects TeX or conversion warnings. It uses no PostScript graphics; use another explicit workflow for PSTricks/TikZ or arbitrary document conversion. A missing package or unsupported macro must be fixed or reported, never silently removed.

## Inline and place components

Paths in a composition file are relative to that JSON file. Canvas dimensions and placements are SVG user units. The example places a diagram at the top and an equation below it:

```json
{
  "width": 600,
  "height": 260,
  "title": "Encoder and reconstruction objective",
  "description": "Input passes through an encoder and decoder; reconstruction is optimized with a squared-error objective.",
  "items": [
    {"file": "architecture.svg", "x": 20, "y": 20, "width": 560, "height": 150},
    {"file": "equation.svg", "x": 180, "y": 195, "width": 240, "height": 40}
  ]
}
```

A nested SVG preserves the component's nonzero viewBox origin and uses aspect-preserving fit within the placement rectangle. The helper renames IDs, `href`/`xlink:href`, local `url(#id)`, and ARIA ID references; it does not resolve arbitrary CSS selectors. Set widths in the composition to match desired equation height. Formula bounding boxes describe visible ink, not a shared text baseline, so align equations visually or supply measured offsets. Do not promise automatic baseline matching.

The composition defaults to a white background so black formula paths remain visible in viewers with dark backgrounds. Set the JSON `background` explicitly if another background or transparency is required. Check text contrast again after changing it.

Ordinary Matplotlib exports may include a DOCTYPE and CSS `<style>` blocks; the strict importer will reject them. They require explicit normalization to presentation attributes before composition, or a different composition tool. Do not silently strip stylesheet content, which can change the figure. The current script does not implement a general SVG/CSS normalizer.

## Export and check

Choose the backend explicitly. CairoSVG supports the bundled path-based equations and basic static geometry; Inkscape has broader editor-specific support and must be installed separately. Text shaping, filters, gradients, and font substitution can differ, so inspect the actual backend output. Export rejects existing output files.

For CairoSVG, use `--width-mm` to set final physical width; for PNG the same width and DPI determine pixel dimensions. Pure vector PDF does not become sharper with higher DPI. Embedded rasters still need sufficient effective resolution. For Inkscape, set physical dimensions in the input SVG; the helper intentionally does not implement `--width-mm` for that backend.

Inspect the preview with an image viewer. Check PDF page size with `pdfinfo` if available. Inspect labels at final manuscript size, rather than judging a large canvas alone. Keep a record of backend, tool versions, output width, source files, and any manual edits.

## Tested local setup

On 2026-10-28, TeX Live 2025 and dvisvgm 3.4.3 generated the bundled equation without warnings. Formula compilation, inline composition, CairoSVG PDF/PNG export, PDF physical width, and rendered appearance were checked. Inkscape was not installed, so its export branch remains untested locally.

On this Apple Silicon machine, CairoSVG is installed in `~/.venv` and native Cairo is in `/opt/homebrew/lib`. A plain import could not locate the native library; an explicit per-command library path worked:

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib ~/.venv/bin/python scripts/svg_tools.py doctor
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib ~/.venv/bin/python scripts/svg_tools.py export /path/figure.svg --backend cairosvg --output /path/figure.pdf --width-mm 89
```

Use this only where the reported library path exists; it is a verified machine-specific setup, not a portable requirement. `doctor` probes the real CairoSVG import and reports its failure rather than treating an installed package as a usable backend. No global shell settings are changed.

## Design references

The [figures4papers repository](https://github.com/ChenLiu-1996/figures4papers), reviewed at `b709de1`, offers real paper examples, consistent semantic colors, dedicated legend panels, and shared styling across subplots. Use it as optional design inspiration rather than as an installed helper library: its skill specifies helper APIs that the consuming project must implement. Do not copy truncated bar baselines or oversized canvases without evaluating the scientific encoding and final print dimensions.

Relevant manuals: [SVG viewBox](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/viewBox), [dvisvgm](https://dvisvgm.de/Manpage/), [CairoSVG](https://cairosvg.org/documentation/), [Inkscape command line](https://inkscape.org/doc/inkscape-man.html), [TexText](https://textext.github.io/textext/).
