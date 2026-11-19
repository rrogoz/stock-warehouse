{#-
    SQL of a generated silver entity (ADR-006, ADR-007, docs/specs/SW-19.md). The model's yml,
    written by `python -m engine.dbt_models` from the entity config, holds what it reads:
    `meta.key` (business key, plus `valid_from_date` if SCD2), `meta.values` (value fields, in
    config order) and the columns, in config order. The stub passes `input`, the staging model,
    because dbt resolves `ref()` while parsing, before the yml is applied.

    Insert-only: an input row is inserted only if its `record_hash` differs from the previous
    version of its key, ordered by `known_at`. In incremental mode the previous version is the
    latest stored one, and input rows not newer than it are skipped. An input row with the key
    and `known_at` of a stored row but another `record_hash` (a same-day correction) fails the
    run; the input is an ephemeral CTE that `run_query` cannot read, so DuckDB's `error()`
    raises it while the model runs.
-#}
{% macro silver_entity(input) -%}
{%- set input_relation = ref(input) -%}
{%- if not execute -%}{{ return('') }}{%- endif -%}
{%- set meta = model.config.meta -%}
{%- set key = meta['key'] -%}
{%- set carried = key + meta['values'] + ['known_at', 'record_hash'] -%}
{%- set columns = model.columns.keys() | list -%}
{%- set on_key %}{% for k in key %}{% if not loop.first %} and {% endif %}candidate.{{ k }} = stored.{{ k }}{% endfor %}{% endset -%}
with

input as (
    select
        {% for field in carried[:-1] %}{{ field }},
        {% endfor %}{{ record_hash(meta['values']) }} as record_hash
    from {{ input_relation }}
),

{% if is_incremental() %}
stored as (
    select
        {% for field in carried %}{{ field }},
        {% endfor %}true as is_stored
    from {{ this }}
    qualify row_number() over (partition by {{ key | join(', ') }} order by known_at desc) = 1
),

conflict as (
    select candidate.*
    from input as candidate
    inner join {{ this }} as stored
        on {{ on_key }} and candidate.known_at = stored.known_at
    where candidate.record_hash != stored.record_hash
),

candidates as (
    select * from stored
    union all
    select
        {% for field in carried %}candidate.{{ field }},
        {% endfor %}false as is_stored
    from input as candidate
    left join stored
        on {{ on_key }}
    where stored.known_at is null or candidate.known_at > stored.known_at
),
{% else %}
candidates as (
    select
        *,
        false as is_stored
    from input
),
{% endif %}

versioned as (
    select
        *,
        lag(record_hash) over (
            partition by {{ key | join(', ') }} order by known_at, record_hash
        ) as previous_hash
    from candidates
)

select
    {% for column in columns %}{% if column == 'run_id' %}cast('{{ var("run_id") }}' as varchar){% else %}{{ column }}{% endif %} as {{ column }}{% if not loop.last %},
    {% endif %}{% endfor %}
from versioned
where not is_stored and previous_hash is distinct from record_hash
{%- if is_incremental() %}
union all
select
    {% for column in columns %}{% if loop.first %}cast(error(
        'same-day correction in {{ model.name }}: key ' || concat_ws(', '{% for k in key %}, cast({{ k }} as varchar){% endfor %})
        || ' at known_at ' || cast(known_at as varchar)
        || ' differs from the stored row; run a full build or record a new recorded_date'
    ) as {{ model.columns[column].data_type }}){% else %}null{% endif %} as {{ column }}{% if not loop.last %},
    {% endif %}{% endfor %}
from conflict
{%- endif %}
{%- endmacro %}
