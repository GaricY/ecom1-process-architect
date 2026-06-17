"""Format SQLite schema discovery output into an agent-friendly view.

Input is the CSV stdout of:

    /bin/sql 'select type, name, sql from sqlite_schema
              where sql is not null order by type, name;'

Output is a compact per-table layout: aligned columns with types and
nullability, FK targets as `→ table.col` arrows on the owning column, and
indexes grouped under their owning table. A "Foreign-key edges" section
auto-derived from FK clauses sits at the top as a one-glance join map.

Parsing handles SQLite's pretty-printed CREATE TABLE / CREATE INDEX output
(tab-indented, one clause per line, trailing commas).
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field


_CREATE_TABLE_RE = re.compile(
    r"CREATE TABLE\s+(\w+)\s*\((.*)\)\s*$", re.DOTALL | re.IGNORECASE
)
_CREATE_INDEX_RE = re.compile(
    r"CREATE INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(([^)]+)\)", re.IGNORECASE
)
_FK_RE = re.compile(
    r"FOREIGN KEY\s*\(\s*(\w+)\s*\)\s+REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)",
    re.IGNORECASE,
)
_PK_RE = re.compile(r"PRIMARY KEY\s*\(([^)]+)\)", re.IGNORECASE)


@dataclass
class SchemaColumn:
    name: str
    type_: str
    not_null: bool


@dataclass
class SchemaTable:
    name: str
    columns: list[SchemaColumn]
    pk_cols: list[str]
    fks: dict[str, tuple[str, str]] = field(default_factory=dict)
    indexes: list[tuple[str, list[str]]] = field(default_factory=list)


def parse_csv_rows(csv_text: str) -> list[tuple[str, str, str]]:
    """Parse CSV stdout of the sqlite_schema discovery query.

    Returns `(type, name, sql)` tuples. Robust to multi-line quoted `sql`
    cells (CREATE TABLE bodies span newlines). Empty/header-only input
    yields `[]`.
    """
    if not csv_text.strip():
        return []
    out: list[tuple[str, str, str]] = []
    reader = csv.reader(io.StringIO(csv_text))
    try:
        next(reader)  # header
    except StopIteration:
        return []
    for row in reader:
        if len(row) >= 3:
            out.append((row[0], row[1], row[2]))
    return out


def _parse_create_table(name: str, sql: str) -> SchemaTable | None:
    m = _CREATE_TABLE_RE.search(sql)
    if not m:
        return None
    body = m.group(2)

    fks: dict[str, tuple[str, str]] = {}
    for fk in _FK_RE.finditer(body):
        fks[fk.group(1).strip()] = (fk.group(2).strip(), fk.group(3).strip())

    composite_pk: list[str] = []
    pk = _PK_RE.search(body)
    if pk:
        composite_pk = [c.strip() for c in pk.group(1).split(",")]

    inline_pk: list[str] = []
    columns: list[SchemaColumn] = []
    for raw in body.splitlines():
        line = raw.strip().rstrip(",").strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("FOREIGN KEY") or upper.startswith("PRIMARY KEY ("):
            continue
        parts = line.split(None, 2)
        if not parts:
            continue
        col_name = parts[0]
        col_type = parts[1] if len(parts) > 1 else ""
        rest_upper = (parts[2] if len(parts) > 2 else "").upper()
        is_pk_inline = "PRIMARY KEY" in rest_upper
        if is_pk_inline:
            inline_pk.append(col_name)
        columns.append(
            SchemaColumn(
                name=col_name,
                type_=col_type,
                not_null=("NOT NULL" in rest_upper) or is_pk_inline,
            )
        )

    return SchemaTable(
        name=name,
        columns=columns,
        pk_cols=composite_pk or inline_pk,
        fks=fks,
    )


def _parse_create_index(sql: str) -> tuple[str, str, list[str]] | None:
    m = _CREATE_INDEX_RE.search(sql)
    if not m:
        return None
    return m.group(1), m.group(2), [c.strip() for c in m.group(3).split(",")]


_SQL_CONVENTIONS_PREAMBLE = """\
## SQL conventions (read me before the first query)

Dialect: **SQLite**. No `ILIKE`, no `RETURNING`, no `::cast`, no `now()`.
`LIKE` is case-insensitive for ASCII; for explicit case-fold use
`LOWER(col) LIKE LOWER('…')`.
`HAVING` requires `GROUP BY` (no MySQL/PG-style alias filter) — to
filter on a computed expression, wrap as a subquery:
`SELECT * FROM (SELECT …, x AS y FROM …) WHERE y > N`.

"""


def build_schema_doc(rows: list[tuple[str, str, str]]) -> str:
    """Render the per-table doc with grouped indexes from sqlite_schema rows."""
    tables: dict[str, SchemaTable] = {}
    by_table_indexes: dict[str, list[tuple[str, list[str]]]] = {}

    for type_, name, sql in rows:
        if type_ == "table":
            tbl = _parse_create_table(name, sql)
            if tbl:
                tables[tbl.name] = tbl
        elif type_ == "index":
            parsed = _parse_create_index(sql)
            if parsed:
                idx_name, tbl_name, cols = parsed
                by_table_indexes.setdefault(tbl_name, []).append((idx_name, cols))

    for tbl_name, tbl in tables.items():
        tbl.indexes = sorted(by_table_indexes.get(tbl_name, []))

    total_idx = sum(len(t.indexes) for t in tables.values())
    lines: list[str] = [
        "# SQLite schema (warehouse DB) — query via /bin/sql",
        f"# {len(tables)} tables, {total_idx} indexes",
        "",
        _SQL_CONVENTIONS_PREAMBLE.rstrip(),
        "",
    ]

    edges: list[tuple[str, str, str, str]] = []
    for tbl_name in sorted(tables):
        for col, (ref_tbl, ref_col) in sorted(tables[tbl_name].fks.items()):
            edges.append((tbl_name, col, ref_tbl, ref_col))
    if edges:
        lines.append("## Foreign-key edges")
        left_w = max(len(f"{t}.{c}") for t, c, _, _ in edges)
        for t, c, rt, rc in edges:
            lhs = f"{t}.{c}"
            lines.append(f"  {lhs:<{left_w}}  → {rt}.{rc}")
        lines.append("")

    lines.append("## Tables (alphabetical)")
    lines.append("")

    for tbl_name in sorted(tables):
        tbl = tables[tbl_name]
        pk_str = f"  PK({', '.join(tbl.pk_cols)})" if tbl.pk_cols else ""
        lines.append(f"TABLE {tbl.name}{pk_str}")

        if tbl.columns:
            name_w = max(len(c.name) for c in tbl.columns)
            type_w = max(len(c.type_) for c in tbl.columns)
            for c in tbl.columns:
                null_str = "NOT NULL" if c.not_null else "        "
                fk_str = ""
                if c.name in tbl.fks:
                    rt, rc = tbl.fks[c.name]
                    fk_str = f"  → {rt}.{rc}"
                lines.append(
                    f"  {c.name:<{name_w}}  {c.type_:<{type_w}}  {null_str}{fk_str}".rstrip()
                )

        if tbl.indexes:
            idx_name_w = max(len(n) for n, _ in tbl.indexes)
            for idx_name, cols in tbl.indexes:
                cols_str = ", ".join(cols)
                lines.append(f"  INDEX {idx_name:<{idx_name_w}}  ({cols_str})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_from_csv(csv_text: str) -> str:
    """Convenience: parse CSV stdout and emit the formatted schema doc."""
    return build_schema_doc(parse_csv_rows(csv_text))
