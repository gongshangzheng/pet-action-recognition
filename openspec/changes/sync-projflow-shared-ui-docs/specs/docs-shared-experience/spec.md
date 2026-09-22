## Purpose

Defines a consistent, safe documentation-reading experience regardless of whether content is served by local FastAPI or a GitHub Pages static build.

## ADDED Requirements

### Requirement: Unicode-safe document addressing
The system SHALL accept non-empty document slugs containing Unicode word characters, spaces, hyphens, and nested path separators, while rejecting absolute paths and traversal segments.

#### Scenario: Unicode document slug is requested
- **WHEN** a client requests a document whose valid slug contains Chinese characters
- **THEN** the system resolves that document using the same slug semantics as an ASCII document

#### Scenario: Traversal slug is requested
- **WHEN** a client requests a slug containing a `..` path segment or an absolute path
- **THEN** the system rejects the request without reading a file outside the documentation root

### Requirement: Deterministic document metadata and ordering
The system SHALL expose document `folder` and `order` metadata and order document lists by folder priority, order, id, descending date, and slug.

#### Scenario: Documents have equal or missing metadata
- **WHEN** multiple documents cannot be distinguished by an earlier sort field
- **THEN** their order is resolved by the next defined field and ultimately slug, producing a stable result

### Requirement: Documentation assets and images
The system SHALL exclude underscore-prefixed directories from document discovery and SHALL make documentation `_assets` images available to development and static readers using safe asset paths.

#### Scenario: Asset directory is scanned
- **WHEN** the documentation directory contains `_assets` or another underscore-prefixed directory
- **THEN** files in that directory are omitted from the document list

#### Scenario: Markdown contains a local asset image
- **WHEN** a document references a valid `_assets` image path
- **THEN** the rendered document displays the image and its non-empty alt text as a caption

### Requirement: Document navigation continuity
The system SHALL preserve a reader's per-document scroll position for ordinary navigation and SHALL prioritize a requested hash anchor over saved position.

#### Scenario: Reader returns to a document
- **WHEN** a reader navigates away from a document and later returns without a hash
- **THEN** the document restores the saved reading position after content renders

#### Scenario: Reader opens an anchored link
- **WHEN** a reader opens or changes a document URL with a hash anchor
- **THEN** the document scrolls to the matching heading after content renders
