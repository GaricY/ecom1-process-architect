# executor_core v0018

- mode: `prod_runtime_contract`
- created_by: `human`
- created_at: `2026-06-19T00:32:33+00:00`
- parent: `v0017`

## Rationale

Teach `executor_core` the generic degraded data-store contract for prod:
when `bin-help/sqlite_schema.txt` was reconstructed from live `/proc`, `/bin/sql`
is treated as unavailable and the Executor should read data through `/proc`
JSON records instead of probing `ws.sql_rows`. This is runtime/tooling guidance
only; it does not name prod task content, concrete prod families, or expected
answers.

## Rollback

Retire/delete `v0018` to return to `v0017` for dev or any runtime where
SQL-first executor guidance is preferred.
