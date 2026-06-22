"""Reconstruct an agent-facing warehouse schema from live `/proc` JSON records.

Bootstrap fallback for when `/bin/sql` is unavailable (the PROD MS SQL cluster
is down). The warehouse is still served as a file-shaped JSON projection under
`/proc/<family>/<partition>/<id>.json`, so `bootstrap` samples a handful of
records per family and hands them here. We infer, per family, the **structure
only**:

- scalar columns with type + nullability (NOT NULL / nullable),
- nested objects (structured ⇒ inlined sub-fields; open-ended maps ⇒ bare
  OBJECT column, no keys),
- nested arrays of objects ⇒ child tables (recursive, any depth),
- foreign-key edges, matched by the prefix of id-like values (`store-…` →
  the family whose own `id` values start with `store-`).

Deliberately NOT emitted (data, not schema — varies per trial): record counts,
column values / enumerations, open-ended map keys, presence ratios. This keeps
the output invariant to warehouse content, so it is identical across trials
whose data differs but whose shape is the same.

The output is rendered into the same `bin-help/sqlite_schema.txt` the executor
reads when `/bin/sql` works — so the agent gets a usable family/field/join map
either way. Everything here is pure (no VM I/O) so the inference is testable;
`bootstrap._recover_schema_from_proc` does the sampling and renders.

Inference is wholly data-driven — NO family names, table names, columns, or
table layout are hard-coded. The only literal field names are the generic
identity/reference conventions (`id`/`ID`/`Id`/`sku`; `*_id`/`*_sku`) used as
PK/FK heuristics — never a benchmark-specific table or column. So it adapts to
per-trial `/proc` renames (`stores` vs `locations`, `returns` vs
`return-workflows`).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

# An object field is an open-ended map (a property bag, keyed per record) rather
# than a structured record (a fixed sub-schema) when its union of keys is both
# large in absolute terms and large relative to the per-record key count. A
# structured object recurses into sub-fields; an open-ended map renders as a
# bare OBJECT column (its keys are data, not schema).
_FREE_FORM_KEYS = 14

# Hard cap on distinct scalar values we retain per field — a memory guard only
# (families are hundreds of records at most). Exceeding it disqualifies the
# field as both an enum and a key.
_DISTINCT_CAP = 5000

# A value is "key-ish" (a candidate identifier) when it starts with a token
# followed by a separator: `basket-0044`, `store-graz-puntigam`, `PT-DRL-…`.
_KEYISH_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*[-_]")
# Leading `<token><sep>` prefix used to match an id reference to its owning
# family (`pay-0006` → `pay-`).
_PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*[-_]")
# ISO-8601-ish timestamp head — excluded from key/enum candidates.
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T")

# Fields whose names mark them as the record's own identity (PK candidates and
# FK targets). Reference fields (`*_id`, `*_sku`) are deliberately NOT keys.
_IDENTITY_NAMES = ("id", "ID", "Id", "sku")
_REF_SUFFIXES = ("_id", "_sku")

# Injected by `ws.read_json`; never a real warehouse column.
_INJECTED_KEYS = ("record_path",)


def _jtype(v: object) -> str:
    """JSON type tag. `bool` is checked before `int` (bools are ints in Python)."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, dict):
        return "object"
    if isinstance(v, list):
        return "array"
    return "other"


def _sql_type(types: set[str]) -> str:
    """Widest SQL-ish type label for the set of JSON scalar types observed."""
    s = types - {"null"}
    if not s:
        return "JSON"
    if "str" in s or "other" in s:
        return "TEXT"
    if "float" in s:
        return "REAL"
    if "int" in s:
        return "INTEGER"
    if s == {"bool"}:
        return "BOOLEAN"
    return "TEXT"


def _prefix(v: str) -> str:
    m = _PREFIX_RE.match(v)
    return m.group(0) if m else v


# ── per-field aggregator ────────────────────────────────────────────────────


@dataclass
class _ColAgg:
    types: set[str] = field(default_factory=set)
    present: int = 0
    nonnull: int = 0
    # scalar distinct values (capped) — for enum + uniqueness/key detection.
    str_distinct: set[str] = field(default_factory=set)
    str_over: bool = False
    int_distinct: set[int] = field(default_factory=set)
    int_over: bool = False
    # nested object records (for structured-vs-free-form + recursion).
    obj_records: list[dict] = field(default_factory=list)
    # nested array element shapes.
    arr_elem_types: set[str] = field(default_factory=set)
    arr_obj_records: list[dict] = field(default_factory=list)
    arr_scalar_distinct: set = field(default_factory=set)
    arr_scalar_over: bool = False

    def observe(self, v: object) -> None:
        self.present += 1
        if v is None:
            self.types.add("null")
            return
        self.nonnull += 1
        if isinstance(v, bool):
            self.types.add("bool")
        elif isinstance(v, int):
            self.types.add("int")
            self._add(self.int_distinct, v, "int_over")
        elif isinstance(v, float):
            self.types.add("float")
        elif isinstance(v, str):
            self.types.add("str")
            self._add(self.str_distinct, v, "str_over")
        elif isinstance(v, dict):
            self.types.add("object")
            self.obj_records.append(v)
        elif isinstance(v, list):
            self.types.add("array")
            for el in v:
                self.arr_elem_types.add(_jtype(el))
                if isinstance(el, dict):
                    self.arr_obj_records.append(el)
                elif isinstance(el, (str, int, float)):  # bool is an int
                    self._add(self.arr_scalar_distinct, el, "arr_scalar_over")
        else:
            self.types.add("other")

    def _add(self, bucket: set, value: object, over_flag: str) -> None:
        if getattr(self, over_flag):
            return
        if value in bucket:
            return
        if len(bucket) >= _DISTINCT_CAP:
            setattr(self, over_flag, True)
            return
        bucket.add(value)


def _aggregate(records: list) -> tuple[list[str], dict[str, _ColAgg], int]:
    """First-seen-ordered columns + per-column aggregates for dict records."""
    order: list[str] = []
    cols: dict[str, _ColAgg] = {}
    n = 0
    for rec in records:
        if not isinstance(rec, dict):
            continue
        n += 1
        for k, v in rec.items():
            if k in _INJECTED_KEYS:
                continue
            agg = cols.get(k)
            if agg is None:
                agg = _ColAgg()
                cols[k] = agg
                order.append(k)
            agg.observe(v)
    return order, cols, n


# ── object / array classification ───────────────────────────────────────────


def _free_form(obj_records: list[dict]) -> tuple[bool, set[str]]:
    key_sets = [set(r.keys()) for r in obj_records if isinstance(r, dict)]
    if not key_sets:
        return False, set()
    union: set[str] = set().union(*key_sets)
    sizes = sorted(len(s) for s in key_sets)
    median = sizes[len(sizes) // 2] or 1
    is_free = len(union) > _FREE_FORM_KEYS and len(union) > 2 * median
    return is_free, union


def _is_object(agg: _ColAgg) -> bool:
    return "object" in agg.types and bool(agg.obj_records)


def _is_array_of_object(agg: _ColAgg) -> bool:
    return "array" in agg.types and bool(agg.arr_obj_records)


def _is_array_of_scalar(agg: _ColAgg) -> bool:
    return "array" in agg.types and not agg.arr_obj_records


def _col_type_label(agg: _ColAgg) -> str:
    if _is_object(agg):
        return "OBJECT"
    if _is_array_of_object(agg):
        return "ARRAY<object>"
    if _is_array_of_scalar(agg):
        elem = _sql_type(agg.arr_elem_types)
        return f"ARRAY<{elem}>" if agg.arr_elem_types else "ARRAY"
    return _sql_type(agg.types)


def _null_note(present: int, nonnull: int, n: int) -> str:
    """`NOT NULL` for a required column, else `""` (nullable).

    A structural flag only — no presence ratios. A field present-and-non-null
    in every sampled record is treated as required; anything optional or
    sometimes-null renders without annotation (the data volume that produced
    that judgement is not part of the schema).
    """
    return "NOT NULL" if (n and present == n and nonnull == n) else ""


# ── foreign-key registry (id-prefix → owning family.key) ─────────────────────


def _key_rank(name: str) -> int:
    if name in ("id", "ID", "Id"):
        return 0
    if name == "sku":
        return 1
    return 2


def _build_key_registry(samples: dict[str, list]) -> dict[str, tuple[str, str]]:
    """Map an id-value prefix to the unique `(family, key)` that owns it.

    Only identity fields (`id`/`ID`/`Id`/`sku`) that are unique and id-shaped
    across the sample qualify as keys, so reference fields (`basket_id`,
    `customer_id`) never pollute the registry. A prefix claimed by two equally
    ranked keys is dropped as ambiguous.
    """
    prefix_owners: dict[str, list[tuple[str, str]]] = {}
    for fam, records in samples.items():
        _, cols, n = _aggregate(records)
        for name in _IDENTITY_NAMES:
            agg = cols.get(name)
            if agg is None or agg.str_over or agg.nonnull == 0:
                continue
            if agg.types - {"null"} != {"str"}:
                continue
            if agg.present < 0.8 * n:
                continue
            if len(agg.str_distinct) != agg.nonnull:
                continue  # not unique ⇒ not a key
            keyish = [
                v
                for v in agg.str_distinct
                if _KEYISH_RE.match(v) and "@" not in v and not _DATE_RE.match(v)
            ]
            if len(keyish) < 0.8 * len(agg.str_distinct):
                continue
            prefs = [_prefix(v) for v in keyish]
            pref, cnt = Counter(prefs).most_common(1)[0]
            if cnt < 0.8 * len(prefs):
                continue
            prefix_owners.setdefault(pref, []).append((fam, name))

    registry: dict[str, tuple[str, str]] = {}
    for pref, owners in prefix_owners.items():
        owners = sorted(owners, key=lambda o: _key_rank(o[1]))
        best = owners[0]
        if len(owners) > 1 and _key_rank(owners[1][1]) == _key_rank(best[1]):
            continue  # ambiguous at the best rank
        registry[pref] = best
    return registry


def _is_reference_name(name: str) -> bool:
    return name == "sku" or any(name.endswith(suf) for suf in _REF_SUFFIXES)


def _fk_target(
    name: str, agg: _ColAgg, registry: dict[str, tuple[str, str]], owner: tuple[str, str]
) -> tuple[str, str] | None:
    """Resolve a reference field to `(family, key)` via its id-value prefix."""
    if not _is_reference_name(name):
        return None
    if "str" not in agg.types or not agg.str_distinct:
        return None
    prefs = [_prefix(v) for v in agg.str_distinct if _KEYISH_RE.match(v)]
    if not prefs:
        return None
    pref, cnt = Counter(prefs).most_common(1)[0]
    if cnt < 0.8 * len(prefs):
        return None
    target = registry.get(pref)
    if not target or target == owner:
        return None
    return target


# ── rendering ────────────────────────────────────────────────────────────────


def _detect_pk(cols: dict[str, _ColAgg], n: int) -> str | None:
    for name in ("id", "ID", "Id"):
        agg = cols.get(name)
        if agg and agg.present == n and agg.nonnull == n:
            return name
    agg = cols.get("sku")
    if agg and agg.present == n and agg.nonnull == n and not agg.str_over:
        if len(agg.str_distinct) == agg.nonnull:
            return "sku"
    return None


def _render_fields(
    out: list[str],
    records: list,
    *,
    family: str,
    path_prefix: str,
    indent: int,
    registry: dict[str, tuple[str, str]],
    fk_edges: list[tuple[str, str]],
) -> None:
    order, cols, n = _aggregate(records)
    pad = " " * indent
    name_w = max((len(k) for k in order), default=1)
    type_w = max((len(_col_type_label(cols[k])) for k in order), default=1)
    children: list[tuple[str, list]] = []

    for k in order:
        agg = cols[k]
        label = _col_type_label(agg)
        nn = _null_note(agg.present, agg.nonnull, n)
        path = path_prefix + k
        base = f"{pad}{k:<{name_w}}  {label:<{type_w}}"
        suffix = f"  {nn}" if nn else ""

        if _is_object(agg):
            is_free, _ = _free_form(agg.obj_records)
            if is_free:
                # Open-ended property map: keys vary per record (data, not
                # schema), so we emit only the column — read a record live for
                # its keys. A structured object recurses into its sub-fields.
                out.append((base + suffix).rstrip())
            else:
                out.append((base + suffix + "  -- nested object").rstrip())
                _render_fields(
                    out,
                    agg.obj_records,
                    family=family,
                    path_prefix=path + ".",
                    indent=indent + 4,
                    registry=registry,
                    fk_edges=fk_edges,
                )
        elif _is_array_of_object(agg):
            out.append(
                (base + suffix + f"  -- child table {family}.{path}").rstrip()
            )
            children.append((path, agg.arr_obj_records))
        else:
            target = _fk_target(k, agg, registry, (family, k))
            if target:
                tgt = f"{target[0]}.{target[1]}"
                fk_edges.append((f"{family}.{path}", tgt))
                out.append((base + suffix + f"  -> {tgt}").rstrip())
            else:
                out.append((base + suffix).rstrip())

    for path, elem_records in children:
        out.append("")
        out.append(
            f"{pad}TABLE {family}.{path}"
            f"  -- one row per element of {family}.{path}"
        )
        _render_fields(
            out,
            elem_records,
            family=family,
            path_prefix=path + ".",
            indent=indent + 2,
            registry=registry,
            fk_edges=fk_edges,
        )


_HEADER_ORIENTATION = (
    "# Structure only: tables, columns, types, nullability, relationships. Record",
    "# counts, column values, and open-ended map keys are NOT shown — they are",
    "# data (vary per trial), not schema. Each TABLE is one",
    "# /proc/<family>/<partition>/<id>.json record type; nested arrays are child",
    "# tables. Read /proc live for actual data: ws.read_json(path) for one record,",
    '# ws.proc("<family>") for a whole family (list /proc live — family names can',
    "# vary per trial). /proc is the source of truth.",
)


def build_recovered_schema_doc(samples: dict[str, dict], *, note: str) -> str:
    """Render the recovered schema doc from per-family sampled records.

    `samples`: `{family: {"records": [dict, ...], "total": int, "sampled": int,
    "truncated": bool}}`. `note` is the one-line provenance line placed in the
    header verbatim.
    """
    families = sorted(samples)
    registry = _build_key_registry(
        {f: samples[f].get("records", []) for f in families}
    )

    fk_edges: list[tuple[str, str]] = []
    family_blocks: list[list[str]] = []

    for fam in families:
        info = samples[fam]
        records = info.get("records", [])
        _, cols, n = _aggregate(records)
        if n == 0:
            continue
        pk = _detect_pk(cols, n)
        pk_str = f"  PK({pk})" if pk else ""
        block: list[str] = [
            "",
            f"TABLE {fam}{pk_str}  -- /proc/{fam}/<partition>/<id>.json",
        ]
        _render_fields(
            block,
            records,
            family=fam,
            path_prefix="",
            indent=2,
            registry=registry,
            fk_edges=fk_edges,
        )
        family_blocks.append(block)

    lines: list[str] = [
        "# Warehouse schema — reconstructed from the live /proc projection.",
        f"# {note}",
        *_HEADER_ORIENTATION,
    ]

    edges = sorted(set(fk_edges))
    if edges:
        lines.append("")
        lines.append("## Foreign-key edges (inferred from /proc id references)")
        left_w = max(len(left) for left, _ in edges)
        for left, right in edges:
            lines.append(f"  {left:<{left_w}}  -> {right}")

    lines.append("")
    lines.append("## Families")
    for block in family_blocks:
        lines.extend(block)

    return "\n".join(lines).rstrip() + "\n"
