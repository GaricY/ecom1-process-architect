# bp_index v0004

- mode: `world_refresh`
- created_by: `process_architect`
- created_at: `2026-05-28T14:54:53+00:00`
- parent: `v0003`

## Rationale

vault-diff added /docs/os-and-tooling-incidents-and-workarounds.md as a sixth Active Decision Policy in /docs/README.md. bp_index must route the new policy's trigger (runtime tool / OS mount / temp directory / generated index / local command reports a known incident with a documented workaround) to the new bp_os_tooling_incidents BP, and the validator requires the new render-path basename (os_tooling_incidents.md) to appear in bp_index content. Cross-cutting principle 3 is updated to note that the active OS/tooling incidents policy is the only place where an 'incident' label maps to a dedicated decision policy; the mutation gate grows one extra item that defers to bp_os_tooling_incidents when a workaround is required.

## Rollback

Restore bp_index v0003 if the executor misroutes the OS/tooling incident trigger or the routing table fails validator format.
