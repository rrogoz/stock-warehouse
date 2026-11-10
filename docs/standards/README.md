# Standards

How we build: the concrete rules every change follows. Each standard meets its requirements in [principles](../principles.md#what-standards-must-guarantee), is checkable by CI or the review agent, and has one agent skill ([ADR-009](../adr/0009-repository-and-standards.md)). A change to a standard needs Rafal's approval (gate 2).

| Standard | Covers | Skill |
| --- | --- | --- |
| [Naming](naming.md) | Layers, entities, fields, sources, files, branches | `standard-naming` |
| [Data modelling](data-modelling.md) | Grain, keys, standard columns, contracts, schema changes | `standard-data-modelling` |
| [Layer boundaries](layer-boundaries.md) | What each layer may read | `standard-layer-boundaries` |
| [Testing](testing.md) | Tests per entity, layer and connector; fixtures | `standard-testing` |
| [Documentation](documentation.md) | Where facts live and how docs are written | `standard-documentation` |
| [Change conventions](change-conventions.md) | Stories, pull requests, code style, review | `standard-change-conventions` |

Skills are added in SW-6. In "How it is checked", **when** says which story builds the check: SW-7 (CI checks), SW-9 (review agent), M1 (checks that need the dbt project).

Use the [template](../templates/standard.md) for a new standard.
