## Purpose

Ensures the GitHub Pages build produces documentation content and assets with behavior equivalent to the local documentation API, without requiring a deployed backend.

## ADDED Requirements

### Requirement: Static documentation metadata parity
The build SHALL generate static document list and detail data containing the metadata and deterministic ordering exposed by the local documentation API.

#### Scenario: Production document list is loaded
- **WHEN** the production application loads the static documentation list
- **THEN** its document slugs and ordering match the local API for the same repository content

### Requirement: Static documentation asset publishing
The build SHALL copy documentation `_assets` into the published static site without treating assets as documents.

#### Scenario: Documentation includes local images
- **WHEN** the documentation source contains files under `_assets`
- **THEN** the production site publishes those files at the document asset URL used by rendered Markdown

### Requirement: SPA deep-link fallback remains available
The production build SHALL publish a `404.html` whose content matches the SPA entry document.

#### Scenario: A Pages document deep link is refreshed
- **WHEN** GitHub Pages receives a request for a client-side documentation route
- **THEN** the SPA fallback can boot the application and render the requested document route
