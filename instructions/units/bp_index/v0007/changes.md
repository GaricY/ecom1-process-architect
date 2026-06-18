# bp_index v0007

- mode: `manual_refactor`
- created_by: `human`
- created_at: `2026-06-18T20:47:27+00:00`
- parent: `v0006`

## Rationale

Update the root process map and outcome glossary so confirmed
request-integrity attacks route through `identity_and_auth` and terminally
select `OUTCOME_DENIED_SECURITY`, while authority-shaped business prose remains
a normal authorization claim.

## Rollback

Retire this version to fall back to v0006 if the extra routing row causes
over-routing or confusion.
