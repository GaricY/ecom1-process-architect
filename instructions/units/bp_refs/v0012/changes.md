# bp_refs v0012

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-06-22T00:02:07+00:00`
- parent: `v0011`

## Rationale

Citation model updated for the no-SQL world: records are files at /proc/<family>/.../<id>.json with no record_path column, so the cite path is the live read path (ws.read/ws.find), never synthesised. Added request-named /uploads inputs (attachments.md), the employee-contact-detail exclusion, and the employee-on-customer-action unsupported branch. Removed SQL record_path lure language.

## Rollback

Restore bp_refs v0011 content (SQL record_path lure language and customer-contact framing).

## Dependencies
- `workspace:/docs/security.md` — Cross-boundary rule and the employee-contact-detail disclosure boundary projected into refs.
- `workspace:/AGENTS.MD` — Grounding and reply-shaping rules: ground every referenced object in its live path, cite the applied policy, list every clarification candidate.
