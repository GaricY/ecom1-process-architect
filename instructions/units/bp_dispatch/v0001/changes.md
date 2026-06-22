# bp_dispatch v0001

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T09:37:50+00:00`

## Rationale

A brand-new dispatch-planning domain was added: AGENTS.MD routes 'plan a dispatch wave pointed to a .md file' to the new /docs/dispatch.md, which defines a wave-file -> package/lane TSV optimization that returns one assignments JSON object maximizing expected net profit. No prior BP covers it; it is information/planning (no commerce mutation) and warrants its own atomic BP.

## Rollback

Remove bp_dispatch from the registry and bp_index routing.

## Dependencies
- `workspace:/docs/dispatch.md` — The wave-file -> package/lane TSV flow, route connectivity rule, priority semantics, the maximize-expected-net-profit objective, the late/missed penalty rule, and the required output JSON shape.
- `workspace:/docs/attachments.md` — Defines /uploads as the input-artifact root for the wave and TSV files.
- `bin_help:cat.help.txt` — The file read tool for the wave and TSV inputs.
