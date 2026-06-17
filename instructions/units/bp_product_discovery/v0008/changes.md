# bp_product_discovery v0008

- mode: `failure_fix`
- created_by: `process_architect`
- created_at: `2026-05-21T12:20:07+00:00`
- parent: `v0006`

## Rationale

On a catalogue claim-verification brief (support note: base product has properties A AND has extra property B; if base exists but extra claim is absent, answer <NO> with the checked SKU), the Executor read the SQL projection, found the base SKU plus a different sibling SKU in the same brand/series/model that carried the extra-claim property, and concluded 'extra claim confirmed' — submitting <YES> with both SKUs in refs. Grader required 'Answer should contain <base-sku>' and the verdict to be <NO>: each products row is one catalogue item with one properties blob (one SKU has one value per property key), so the brief's 'and has pack count 100 pcs' claim layered on top of a base 'pack count 500 pcs' is an assertion about the same SKU carrying both, which cannot be true; a sibling SKU with the 100-count value is a separate item the brief did not ask about. The Executor also put nothing identifying in the message, so even a corrected <NO> verdict would have missed the 'include the checked SKU' literal-match in the grader. The new 'Catalogue claim verification' section narrows what 'extra catalogue claim' means (same SKU, not sibling row), spells out the verdict table, and adds a message-shape rule that any literal the brief tells you to include must live in submit_and_exit(message=...) and not only in refs. Two anti-patterns name both failure modes. Dependency set is unchanged from v0006 (sql.help.txt is now load-bearing for the 'one SKU, one value per property key' rule, but it was already a declared dependency).

## Rollback

Create a new version from v0006 content if the claim-verification rule starts flipping legitimate <YES> answers to <NO> on briefs that genuinely ask whether the product LINE (not the base SKU) covers a set of properties between its variants.

## Dependencies
- `workspace:/docs/README.md` — Source of the catalogue reporting rule and the dated-update folder list used by step 3 of the BP; unchanged from v0006.
- `workspace:/AGENTS.MD` — Source of the reply-shaping rule 'availability answers reference only what is available'; step 6 of the BP extends it to refs. Unchanged from v0006.
- `bin_help:sql.help.txt` — Defines products / product_properties / inventory / stores table shapes. The new Catalogue claim verification section is load-bearing on the 'products row carries one properties blob and product_properties is keyed on sku' shape — one SKU has one value per property key — which is the basis for treating an extra claim as a same-SKU property check rather than a sibling-row hunt.
- `bin_help:date.help.txt` — Step 3 still makes /bin/date the only trusted source for the operating-day comparison on dated updates; the BP is wrong if /bin/date's contract changes. Unchanged from v0006.
- `bin_help:id.help.txt` — Step 1 calls /bin/id at session start; the BP's actor handling depends on its output shape. Unchanged from v0006.
