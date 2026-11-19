-- Hand-written: reference data has no source config (ADR-007 escape hatch, docs/specs/SW-19.md).
select
    cast(instrument_code as varchar) as instrument_code,
    cast(valid_from_date as date) as valid_from_date,
    cast(current_symbol as varchar) as current_symbol,
    cast(asset_class as varchar) as asset_class,
    cast(exchange as varchar) as exchange,
    cast(quote_ccy as varchar) as quote_ccy,
    cast(cast(recorded_date as date) as timestamp) at time zone 'UTC' as known_at
from {{ source('reference', 'instrument_versions') }}
