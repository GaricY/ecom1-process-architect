# executor_core v0014

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-30T09:26:00+00:00`
- parent: `v0013`

## Rationale

Prod SQL cluster outage (run 20260530-111534, t001): /bin/sql is down, so ws.sql_rows raises a cluster-down RuntimeError on every warehouse read — the executor looped retrying SQL (even sleeping 9s) and the trial was killed. The organizer exposed the same warehouse as a file-shaped JSON projection under /proc/<family>/.../<id>.json, readable via the file-RPCs and the newly-added /bin/jq (confirmed: ws.search/find/read/list all reach /proc). Companion to static-instructions/workspace.py, which gained ws.proc (bulk /proc record loader = SELECT * replacement, built on the audited ws.read so the Process Architect's vault/proc replay survives — NOT /bin/cat), ws.read_json (single-record parse + injected record_path), ws.jq (thin /bin/jq wrapper), plus a directive cluster-down error on ws.sql_rows. This executor_core version: (1) rewrites the 'Calling SQL' section into 'Reading warehouse data' — health-aware (/proc by default; ws.sql_rows only if a trial's /bin/sql actually answers; never retry a cluster-down call in a loop), narrow-first (ws.search/ws.find then ws.read_json), bulk-scan via ws.proc; (2) teaches live family discovery via ws.list('/proc') because prod relocates family names per trial (stores vs locations, returns vs return-workflows — observed across trials 0009/0022 of the same run; matches memory ecom-prod-proc-no-docs-and-dev-baseline); (3) live shape confirmation (sqlite_schema.txt is a map that can lag the world); (4) ws-surface bullets add read_json/proc/jq and demote sql_rows/sql to the recovery path; (5) the sqlite_schema.txt local-snapshot bullet + the 'before writing any SQL' lead-ins reframed as 'the warehouse map / before any warehouse read'. Kept fully schema-agnostic (only <family>/<text>/<partition> placeholders) per the world_refresh-frozen constraint (memory executor-core-is-world-refresh-frozen). The BP-layer SQL->/proc migration is owned separately by the world_refresh PA (dry-ran as ...-process-architect-world-refresh-v0004). Prose-only; dependency contract unchanged (empty).

## Rollback

Revert to v0013 (bp_admin rollback executor_core --from v0013, or retire v0014) if executors regress on warehouse reads — e.g. emit a literal <family> placeholder, stop discovering families live, or stop citing record_path. If /bin/sql recovers permanently a later version can restore SQL primacy, but keep the /proc path documented since SQL and /proc are the same warehouse projection.
