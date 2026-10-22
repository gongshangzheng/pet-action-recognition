## ADDED Requirements

### Requirement: Single control point for hidden entries

Menu and feature entry visibility SHALL be controlled by a single configuration list, and hiding an entry SHALL NOT remove its route.

#### Scenario: Hide a menu group

- **WHEN** a group key is present in the hidden-entry configuration
- **THEN** the sidebar renders without that group and all of its children, while its routes remain reachable by direct URL

#### Scenario: Hide a single menu item

- **WHEN** a route path is present in the hidden-entry configuration
- **THEN** only that sidebar item disappears and sibling items stay visible

#### Scenario: Restore a hidden entry

- **WHEN** a key is removed from the hidden-entry configuration
- **THEN** the corresponding group or item reappears without further code changes

#### Scenario: Default configuration keeps the full menu

- **WHEN** the hidden-entry configuration is empty
- **THEN** every menu entry defined by the layout is visible
