# bp_product_discovery v0020

- mode: `failure_fix`
- created_by: `human`
- created_at: `2026-05-30T10:48:49+00:00`
- parent: `v0019`

## Rationale

Run 20260530-125612 (ecom1-prod): yes/no token regression (live /AGENTS.MD = ja/nein). This BP echoed the stale literal TRUE(1)/FALSE(0) twice (claim-verification message shape + anti-pattern). De-hardcoded both to 'read the yes/no token from the live /AGENTS.MD' so no prompt file leaks the stale literal.

## Rollback

bp_admin rollback bp_product_discovery --from this version if the live-read phrasing regresses claim-verification trials.

## Dependencies
- `workspace:/docs/catalogue-lookup.md` — Catalogue resolution rule (resolve to exactly one product, else clarify and cite candidate SKUs); replaces the removed /docs/README.md catalogue reporting rule.
- `bin_help:jq.help.txt` — JSON read tool for catalogue/store data now that /bin/sql is unavailable.
- `bin_help:cat.help.txt` — Raw record read tool for catalogue/store JSON.
- `bin_help:date.help.txt` — Operating-day source for any dated catalogue reporting rule.
- `bin_help:id.help.txt` — Actor identity pulled at session start.
