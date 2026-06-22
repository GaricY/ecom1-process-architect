# bp_dispatch v0002

- mode: `refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T18:09:21+00:00`
- parent: `v0001`

## Rationale

Dep drift in /docs/attachments.md renamed the upload root from /uploads to /storage. The bp_dispatch text named /uploads in two places (Inputs and Refs) as the typical location for the wave .md and TSV input artifacts; both references are updated to /storage and the Dependencies prose now describes /storage as the input-artifact root. No other policy gates changed.

## Rollback

Revert pa-output/units/bp_dispatch/content.md to the v0001 content (which named /uploads instead of /storage) and re-record the v0001 attachments.md dep hash.

## Dependencies
- `workspace:/docs/dispatch.md` — Authoritative dispatch-planning policy: wave-file -> package/lane TSV flow, route connectivity rule, priority semantics, maximize-expected-net-profit objective, late/missed penalty rule, and the required output JSON shape.
- `workspace:/docs/attachments.md` — Defines /storage as the upload root for input artifacts; the BP names this path as the typical location for the wave .md and TSV files.
- `bin_help:cat.help.txt` — /bin/cat is the file-read tool the Executor uses to load the wave .md and TSV inputs.
