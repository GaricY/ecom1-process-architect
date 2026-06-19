# bp_refs v0011

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-19T17:06:00+00:00`
- parent: `v0010`

## Rationale

Move topic-specific refs policy out of the shared refs process. bp_refs now owns the shared Evidence ledger model, privacy/cross-boundary citation safety, live-path projection, request-named input class, request-integrity denial projection, and final refs checklist. Topic BPs own applied topic docs, public/private record classification, domain-specific evidence, and exact branch-local refs_must_include / refs_must_not_include.

## Rollback

Retire this version to fall back to v0010 if removing topic-specific public-record or topic-doc guidance from refs causes under-citation before topic BPs are corrected.

## Dependencies
- `workspace:/AGENTS.MD` — Top-level grounding-reference rules: full repo path for referenced objects, applied-policy citation, and candidate refs for clarification.
- `workspace:/docs/security.md` — Authority for cross-boundary and personal-information citation boundaries.
