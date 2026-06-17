# executor_core v0007

- mode: `manual_update`
- created_by: `human-ws-sql-rows-paging`
- created_at: `2026-05-23T14:04:00+00:00`
- parent: `v0006`

## Rationale

Reflect the new `ws.sql_rows` contract from `workspace.py`:

- signature is now `sql_rows(query, limit=1000)` returning
  `{"rows": list[dict], "row_count": int, "truncated": bool}`
  (was: bare `list[dict]`);
- helper transparently pages under the harness 100-row cap, so the
  query goes to `/bin/sql` unchanged in the common case;
- `truncated=True` means the result was capped at `limit` AND at
  least one more row was available — caller walks further with an
  explicit `LIMIT/OFFSET` re-issue.

Two prose changes to `content.md`:

1. `ws` surface listing — new `sql_rows` signature + a clear
   "**Do not use `ws.sql` for normal SELECTs**" warning naming the
   real harness footer (`warning: result truncated at 100 rows`)
   so the agent recognises the failure mode if it ignores the rule.
2. "Calling SQL" section — new dict-return example, canonical
   `LIMIT/OFFSET + ORDER BY` paging recipe (with `PAGE = 500` so
   it does not look like the `limit=1000` default), tip to bump
   `limit=` on bounded queries instead of rolling a pager. Removed
   the false v0006 comment about "back-to-back JSON arrays" — the
   harness never emitted that shape; that text was describing
   non-existent behaviour and bred copy-paste foot-guns.

Internals (`/bin/sql` 100-row cap, the regex that parses the
truncation footer, the subquery-wrap auto-pager) are intentionally
NOT in the prompt — agent only sees the caller-facing contract.

## Rollback

To restore prior text run: uv run python -m orchestrator.bp_admin rollback executor_core --from v0006 --empty-deps
