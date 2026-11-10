# Standard: Documentation

One page at most. Skill: `standard-documentation`.

## Purpose

Each fact has one home in the repository, kept true in the same change, and short enough for people and agents to read ([requirements](../principles.md#what-standards-must-guarantee), [ADR-009](../adr/0009-repository-and-standards.md)).

## Rules

- **One home per fact,** as in the ADR-009 table. Everything else links to it, never copies.
- **Every entity is documented in its config:** purpose, grain, key, each field's meaning and unit, lineage (sources and upstream entities). dbt docs render it.
- **Every source** is documented in its source config: what it provides, its calendar, terms of use link.
- **Docs change with the code,** in the same pull request. Docs that disagree with the code are a bug.
- **Decisions are ADRs** on the [template](../templates/adr.md), with context, decision, consequences, options and status, listed in the [index](../adr/README.md).
- **Specs** follow the [template](../templates/spec.md); before merge, lasting facts move into docs or config, then the spec is frozen.
- **Terms** are defined once, in the [glossary](../glossary.md), in the change that first uses them.
- **Writing:** first line says what the document is for; plain words, short sentences, active voice; bullets and tables over paragraphs; one example per rule, from this project; diagrams in Mermaid; English only.
- **Length:** README, each standard and each ADR up to one page; a spec up to two; a runbook is numbered steps only.

## Example

Adding `ref_trading_calendar` updates `config/entities/ref_trading_calendar.yaml` (purpose, grain, fields), adds "Session" to the glossary if missing, and links the calendar ADR, all in one pull request.

## How it is checked

| Rule | Check | When |
| --- | --- | --- |
| Every entity and field documented | CI docs coverage check on entity configs | M1 |
| Links resolve; template sections present; ADR status valid | CI docs check | SW-7 |
| Change updates every doc it affects | Review agent | SW-9 |
| Plain, short, linked not copied | Review agent | SW-9 |
