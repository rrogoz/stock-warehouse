-- Hand-written: reference data has no source config (ADR-007 escape hatch, docs/specs/SW-19.md).
select
    cast(instrument_code as varchar) as instrument_code,
    cast(source as varchar) as source,
    cast(valid_from_date as date) as valid_from_date,
    cast(source_instrument_id as varchar) as source_instrument_id,
    cast(cast(recorded_date as date) as timestamp) at time zone 'UTC' as known_at
from {{ source('reference', 'instrument_source_ids') }}
