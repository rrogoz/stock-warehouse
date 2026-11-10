# ADR-005: Sources and ingestion

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

M1 needs one free, reliable source for currencies, and ingestion must be the same for history and daily loads.

## Decision

- **M1 source: the NBP API:** official PLN reference rates, one per Polish business day, since 2002. Stored in `fact_price_daily` as `close` with `price_type = fixing`; open, high and low stay empty.
- **Stooq only after a spike story in M1** checks adjustment around a GPW dividend (D7), access and terms of use.
- **Calendars are reference files** in `reference/`, generated from `exchange_calendars` (`XWAR`) and Polish public holidays (`NBP`). Each new year's file is a change Rafal approves. Never derived from price data.
- **One connector per source; the shared engine runs the steps** ([ADR-007](0007-pipeline-engine-and-operations.md)).
- **Contract tests on synthetic sample responses** shaped like the real ones; tests never call a real source.
- **One code path for history and daily:** history is the same connector run over past windows (93-day chunks for NBP).
- **Daily runs re-fetch the last 5 sessions** to catch late corrections; deduplication keeps this from adding rows.
- **Polite fetching:** rate limiting, retries with back-off, timeouts. A failed fetch fails the run visibly, and the completeness gate holds downstream steps.
- **Idempotent reruns:** rerunning a day adds bronze files but never duplicate silver rows.
- **Reconciliation (D9) is designed at M4,** when a second source for the same data arrives.

## Consequences

- M1 has no OHLC data; gold must handle fixings.
- Calendars need a yearly approved update.

## Options considered

- Stooq as the first source: access and terms unclear, history appears back-adjusted.
- A calendar derived from price data: circular.

Sources: [NBP API](https://api.nbp.pl/), [exchange_calendars](https://pypi.org/project/exchange-calendars/).
