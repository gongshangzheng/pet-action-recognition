# docs-page-content Specification

## Purpose
TBD - created by archiving change sync-projflow-oct. Update Purpose after archive.
## Requirements
### Requirement: Mathematical formula rendering

The documentation page SHALL render LaTeX math written in Markdown as typeset formulas instead of raw source text.

#### Scenario: Display block formula

- **WHEN** a document body contains `$$ … $$` on its own paragraph
- **THEN** the page renders a centered, typeset block formula

#### Scenario: Display inline formula

- **WHEN** a document body contains `$ … $` inside a sentence
- **THEN** the page renders the expression inline within that sentence without breaking line flow

#### Scenario: Formula inside Mermaid label

- **WHEN** a Mermaid node or edge label contains a LaTeX expression
- **THEN** the diagram renders the typeset expression without clipping the label text

### Requirement: Documentation asset URL resolution across data sources

The documentation reader SHALL resolve the same asset URLs regardless of whether content comes from the local API or the build-time static dataset.

#### Scenario: Static build renders document images

- **WHEN** the production build serves document content containing `/api/management/docs-assets/<file>`
- **THEN** the image resolves against the published `docs-assets/` path under the deployment base URL

#### Scenario: Local development renders document images

- **WHEN** the dev server serves document content containing `/api/management/docs-assets/<file>`
- **THEN** the image resolves through the backend static endpoint unchanged

