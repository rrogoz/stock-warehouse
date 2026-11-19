{#- Hash of the value fields in config order: text, null as \N, joined by chr(31), md5
    (ADR-004 data rules). -#}
{% macro record_hash(fields) -%}
    md5(concat_ws(chr(31){% for field in fields %}, coalesce(cast({{ field }} as varchar), '\N'){% endfor %}))
{%- endmacro %}
