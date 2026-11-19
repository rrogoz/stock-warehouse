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
| Closure | A weekday without a session in a trading calendar: a holiday or an ad hoc closure. Listed with its name in the calendar file. |
| Connector | The source-specific code: `fetch` and `parse`. Everything else is config and the shared engine ([ADR-007](adr/0007-pipeline-engine-and-operations.md)). |
| Contract | The versioned definition of a silver entity: fields, types, key, rules. Used by tests and external producers. |
| Current symbol | The symbol an instrument is shown under today; it may change, the permanent code does not. FX: base and quote currency without separator, for example `EURPLN`. |
| Entity config | The YAML file in `config/entities/` that defines and documents an entity, validated by [its schema](../config/schemas/entity.schema.json); dbt macros generate its SQL, and `python -m engine.dbt_models` its contract and tests, from it. |
| Full build | A dbt run with `--full-refresh`: every dbt-built silver table is rebuilt from all its input. Gives the same rows as incremental builds on the same input. |
| Fixing | An official reference rate published once per day, such as an NBP rate. Stored as `close` with `price_type = fixing`. |
| Gate | A point where Rafal must approve: spec, ADR or standard change, identity or source switch, release to PROD. |
| Grain | What one row of an entity means, in one sentence, for example one price per instrument, business date and source. |
| Incremental build | The normal dbt run: each silver table keeps its rows and gains only input rows newer than its latest version per key, with a new `record_hash`. |
| Instrument register | The reviewed file [`reference/instrument_register.yaml`](../reference/instrument_register.yaml) that defines every instrument's identity and source identifiers, validated by [its schema](../config/schemas/instrument_register.schema.json). |
| Known at | When we learned a record: the fetch time of its bronze file, in UTC. Column `known_at` (D13). |
| Permanent code | An instrument's identity, assigned once and never changed or reused, for example `FX.EURPLN` ([ADR-004](adr/0004-physical-data-model.md)). |
| Pointer | The object `warehouse/current.json` that names the published database file. Written last in a run, so an interrupted run leaves the old version current; restoring means pointing it back ([ADR-003](adr/0003-storage-and-physical-format.md), [runbook](runbooks/run-the-pipeline.md)). |
| Point in time | Data shown as it was known at a past moment, with nothing learned later (D11, D13). |
| Pre-release check | CI run of a release candidate on the last 30 sessions of real data, in throwaway storage, before Rafal approves it ([ADR-002](adr/0002-runtime-and-environments.md)). |
| Quarantine | Where rejected rows go, with a reason, instead of being dropped or guessed. Table `ops_quarantine`. |
| Quote status | Per instrument and session: traded, suspended, or missing on our side (D14). |
| Recorded date | The date a fact was written to the instrument register, next to its valid-from date, so the register is point in time. Field `recorded_date`. |
| Record hash | Hash of a record's normalised value columns, used to skip unchanged rows. Column `record_hash`. |
| Release candidate | The image built for every merge to main, tagged with date and short commit ([ADR-008](adr/0008-ci-cd-and-release.md)). |
| Run id | The id of one pipeline run, stamped on bronze metadata and silver rows, and logged in [`ops_run_log`](../config/entities/ops_run_log.yaml). |
| Run log | The insert-only objects under `ops/run_log/` (`started.json`, `ended.json` per run) and the table `silver.ops_run_log` rebuilt from them each run. |
| SCD2 | Keeping every version of a reference record with its valid-from date, instead of overwriting it. |
| Session | One trading day of a market or one publication day of a source, per its trading calendar (see Trading calendar). |
| Skill | Short agent instructions for one role or one standard, in `.claude/skills/`; it links to the docs, never copies them ([ADR-011](adr/0011-agent-orchestration.md)). |
| Source identifier | A source's own identifier for an instrument, mapped to its permanent code in the instrument register, for example NBP `A/EUR` for `FX.EURPLN`. Field `source_instrument_id`. |
| Source config | The YAML file that holds everything about a source except fetch and parse. |
| Spec | A story's technical specification in `docs/specs/`; frozen after merge. |
| Staging | dbt models per source between bronze and silver: rename, cast, register lookup and quarantine, generated from the source config. Reference data has no source config, so its staging models (`dbt/models/staging/reference/`) are hand-written, the custom-model escape hatch of [ADR-007](adr/0007-pipeline-engine-and-operations.md). |
| Supervised mode | M1 rule: Rafal approves every pull request ([ADR-011](adr/0011-agent-orchestration.md)). |
| Trading calendar | The reviewed list of sessions of `XWAR` or `NBP` for one year: a file in [`reference/calendars/`](../reference/calendars/) validated by [its schema](../config/schemas/trading_calendar.schema.json). Sessions are the weekdays of the year minus its closures. |
