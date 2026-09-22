## Context

The existing `static-docs-for-pages` change provides build-time JSON and an SPA fallback, while local development reads documents from FastAPI. The documented shared experience additions must retain parity across those two sources and must not reintroduce a Pages backend dependency.

## Goals / Non-Goals

**Goals:**
- Keep API and static generator metadata and ordering equivalent.
- Serve and publish documentation image assets safely.
- Make document anchors and reading location resilient to client-side navigation.

**Non-Goals:**
- Static generation of non-document management APIs.
- Changes to Vite base, deployment workflow, or the completed shared theme/favicons change.
- Rendering arbitrary Markdown HTML.

## Decisions

### D1: Mirror document semantics in the backend and build generator
Both data producers use the same folder/order/id/date/slug ordering contract and omit underscore-prefixed directories.

- Rationale: a reader must not observe a different sidebar order in development and Pages.
- Alternative: allow each source to use native filesystem order; rejected because it creates nondeterministic parity bugs.

### D2: Publish only the documentation asset root
FastAPI maps only `management/docs/_assets`; the static generator copies only that directory to the published `docs-assets` path.

- Rationale: this provides required images without widening readable filesystem scope.
- Alternative: serve all `management/docs`; rejected because it exposes source Markdown and sidecars unnecessarily.

### D3: Hash wins over remembered scroll position
Route hash navigation waits for rendered content; if no matching hash is present, scroll restoration waits for the scrollable container and document content.

- Rationale: shared document links must be reliably addressable, while ordinary back-and-forth navigation retains reader context.
- Alternative: restore saved position first; rejected because it would make direct heading links unreliable.

### D4: Render only safe Markdown output
Raw Markdown HTML is disabled. A paragraph consisting only of a captioned image is represented as a figure with a figcaption.

- Rationale: prevents arbitrary HTML insertion while supporting semantic documentation images.

## Risks / Trade-offs

- [API and static generator logic diverges in a future edit] → validate their slug ordering in a build-time assertion.
- [Asset references attempt traversal] → reject invalid asset path segments before rewriting the rendered URL.
- [Saved scroll state is stale] → reset to the top when no valid saved value can be restored.
- [Large bundles already trigger Vite warnings] → retain existing build structure; this change does not add dependencies or bundle all document content.

## Migration Plan

1. Add API and build-generator parity for slug validation, metadata, sorting and assets.
2. Add client navigation, safe Markdown image rendering and asset URL resolution.
3. Run Python route checks, static/API parity assertions, production build and artifact checks.
4. Commit with ProjFlow source attribution, push `origin/main`, then verify GitHub Pages deployment.
5. Roll back by reverting the implementation commit; source documents and generated build artifacts remain unchanged in version control.
