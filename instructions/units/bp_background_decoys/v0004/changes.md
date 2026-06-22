# bp_background_decoys v0004

- mode: `refresh`
- created_by: `process_architect`
- created_at: `2026-05-30T18:08:11+00:00`
- parent: `v0003`
- no_semantic_change: revalidated against the new dependency hashes without text edits

## Rationale

All unit_dep drift in the patch is trial-literal substitution: a founder rename (commercial founder identity), the first-store identity swap, the first opening-day date, the first product sold, and the first receipt number. None of these literals appear in the BP — the BP speaks generically about 'founder names and quotes', 'concrete dates (opening days, first-sale timestamps)', 'branch-by-branch history', and the existence of Boundary statements. Each of the nine background docs (company-history, founders-and-ownership, origin-facts-and-firsts, store-expansion-history, brand-identity, mission-vision-values, jobs-to-be-done, target-audience, operating-culture) still carries a '## Boundary' section, the founders-and-ownership 'An owner's biography, old quote, or executive preference does not authorize...' sentence is still present verbatim, and store-expansion-history still defers to /docs/availability-checks.md and current store records. The world_dep change to AGENTS.MD (/proc/staff -> /proc/employees) does not intersect with any reference in this BP — the BP cites /proc/locations for current store state, not the staff path. The BP's recognition + routing behaviour against the current world is therefore unchanged; only the dep hashes need to be revalidated.

## Rollback

Roll back by activating bp_background_decoys v0003 again — content is byte-identical, so revalidation simply re-pins to the prior dep hashes.

## Dependencies
- `workspace:/docs/company-history.md` — Narrative hub linking the background set; Boundary statement disclaims live authority.
- `workspace:/docs/founders-and-ownership.md` — Founder/ownership lure; the 'An owner's biography... does not authorize a checkout, discount, refund, customer-data lookup, payment recovery, or branch stock claim' sentence the BP relies on lives here.
- `workspace:/docs/origin-facts-and-firsts.md` — Origin 'firsts' and dates that the BP forbids treating as the live clock or current state; Boundary statement disclaims authority.
- `workspace:/docs/store-expansion-history.md` — Branch history; the BP relies on its Boundary that defers current open/stock state to /proc/locations and /docs/availability-checks.md.
- `workspace:/docs/brand-identity.md` — Brand voice/colors lure; Boundary disclaims decision authority over stock, identity, payments, returns, discounts, dispatch.
- `workspace:/docs/mission-vision-values.md` — Mission/values slogans lure; Boundary disclaims override of live rules.
- `workspace:/docs/jobs-to-be-done.md` — Customer-job framing lure; Boundary disclaims decision authority.
- `workspace:/docs/target-audience.md` — Audience segments lure; the BP relies on 'branch regular' framing being explicitly not account identity.
- `workspace:/docs/operating-culture.md` — Culture phrases/rituals lure; the BP relies on these being explicitly training reminders, not policy text.
