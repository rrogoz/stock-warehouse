# Glossary

Business and project terms, each defined once. Other docs link here instead of redefining them. Add a term in the same change that first uses it.

| Term | Meaning |
| --- | --- |
| Adjustment basis | How a price series treats corporate events: `raw`, split-adjusted or total return. Never mixed in one series (D7). |
| As-of date | The date a feature or label describes; it may use only data known by then (D11). |
| Bootstrap story | An M0 story built by Rafal with Claude Code, outside the agent flow and the metrics. |
| Bronze, silver, gold | The three layers: raw files per source; canonical entities; features and data products ([ADR-001](adr/0001-medallion-with-canonical-model.md)). |
| Business date | The date a record describes, for prices the trading day in the exchange's calendar. Column `business_date`. |
| Business key | The natural key of an entity, such as instrument code plus business date plus source. Silver uses only business keys. |
| Completeness gate | The silver check that every expected instrument and session is present or has a quote status. If it fails, gold is not rebuilt (D14). |
| Connector | The source-specific code: `fetch` and `parse`. Everything else is config and the shared engine ([ADR-007](adr/0007-pipeline-engine-and-operations.md)). |
| Contract | The versioned definition of a silver entity: fields, types, key, rules. Used by tests and external producers. |
| Entity config | The YAML file that defines a silver entity; dbt macros generate its SQL and tests from it. |
| Fixing | An official reference rate published once per day, such as an NBP rate. Stored as `close` with `price_type = fixing`. |
| Gate | A point where Rafal must approve: spec, ADR or standard change, identity or source switch, release to PROD. |
| Grain | What one row of an entity means, in one sentence, for example one price per instrument, business date and source. |
| Instrument register | The reviewed file in `reference/` that defines every instrument's identity and source identifiers. |
| Known at | When we learned a record: the fetch time of its bronze file, in UTC. Column `known_at` (D13). |
| Permanent code | An instrument's identity, assigned once and never changed or reused, for example `FX.EURPLN` ([ADR-004](adr/0004-physical-data-model.md)). |
| Point in time | Data shown as it was known at a past moment, with nothing learned later (D11, D13). |
| Pre-release check | CI run of a release candidate on the last 30 sessions of real data, in throwaway storage, before Rafal approves it ([ADR-002](adr/0002-runtime-and-environments.md)). |
| Quarantine | Where rejected rows go, with a reason, instead of being dropped or guessed. Table `ops_quarantine`. |
| Quote status | Per instrument and session: traded, suspended, or missing on our side (D14). |
| Record hash | Hash of a record's normalised value columns, used to skip unchanged rows. Column `record_hash`. |
| Release candidate | The image built for every merge to main, tagged with date and short commit ([ADR-008](adr/0008-ci-cd-and-release.md)). |
| Run id | The id of one pipeline run, stamped on bronze metadata and silver rows, and logged in `ops_run_log`. |
| SCD2 | Keeping every version of a reference record with its valid-from date, instead of overwriting it. |
| Session | One trading day of a market or one publication day of a source, per its calendar. |
| Source config | The YAML file that holds everything about a source except fetch and parse. |
| Spec | A story's technical specification in `docs/specs/`; frozen after merge. |
| Staging | dbt models per source between bronze and silver: rename, cast, register lookup and quarantine, generated from the source config. |
| Supervised mode | M1 rule: Rafal approves every pull request ([ADR-011](adr/0011-agent-orchestration.md)). |
