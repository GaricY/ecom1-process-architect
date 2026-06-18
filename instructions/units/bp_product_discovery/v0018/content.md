# Product Discovery and Inventory

## When this process applies

A question about catalogue, product properties, store list, store hours, or "is X available today at Y?" / "how many products of kind Z?". Also covers **catalogue claim-verification** questions where a support note / message / brief attributes a set of properties to a specific product line and asks the actor to confirm or deny the claim against the live catalogue. Information-only — never mutates. If the request is "my basket / order / payment", route through [identity_and_auth](identity_and_auth.md) and the relevant action BP; this file is for the public catalogue and inventory projection.

## Inputs

- Live workspace paths:
  - `/proc/catalog/<sku>.json` — generated product record per `sku`. **The canonical cite is the `product_variants.record_path` column copied verbatim from SQL** — NOT a hand-built `/proc/products/<sku>.json` (the SQL table is named `product_variants`, but the on-disk folder is `/proc/catalog/`; do not synthesise the path from the table name).
  - `/proc/stores/<id>.json` — store record. Same rule: cite the `stores.record_path` column verbatim, not a synthesised path.
  - `/proc/stores/README.md` — source for natural-language branch nuance in cities with multiple stores; read it live before choosing between branches.
  - `/docs/README.md` — defines the "today's catalogue reporting rule" and where dated overrides may live.
  - `/AGENTS.MD` — the merchant-wide reply-shaping rule that pure availability answers reference only what **is** available; step 7 separates that rule from non-pure catalogue identity/match claims.
- Tools: `/bin/sql` — the only source of catalogue and inventory truth. See [`bin-help/sql.help.txt`](../bin-help/sql.help.txt). Tables: `product_variants`, `product_variant_properties`, `product_categories`, `product_families`, `product_kinds`, `store_inventory`, `stores`. Every public table carries a `record_path TEXT NOT NULL` column whose value is the on-disk `/proc/...` cite path. `/bin/date` — the only trusted source of the simulation's "today"; see [date_and_time](date_and_time.md).

## Process

For catalogue count/reporting update semantics, invoke [policy_update_scan](policy_update_scan.md). This file owns catalogue/inventory SQL and reply shaping; the helper owns bounded update matching and date-scope interpretation.

1. Call `/bin/id` (cheap, also drives "my" handling). Identity is informational here; discovery answers do not depend on actor.
2. For any store-scoped inventory/availability question, resolve the selected store row first and copy `stores.record_path` from SQL or the live record. If the city has multiple branches or the request uses branch wording such as west-side, north, station-side, old-town, downtown, or central, read `/proc/stores/README.md` and use that live nuance before choosing the one store; keep rejected stores out of `refs`.
3. For an availability question: `SELECT available_today_quantity FROM store_inventory WHERE store_id = ? AND product_sku = ?` (or the equivalent batch query for a list). `store_inventory` is keyed by `(store_id, product_sku)`; missing row means not stocked at that store. Treat both **no inventory row** (LEFT JOIN returns `NULL`) and `available_today_quantity = 0` as "not available today" — neither contributes to a positive availability answer.
4. For "how many products of kind X today?" or any catalogue **count** question: invoke [policy_update_scan](policy_update_scan.md) before answering with a plain `COUNT(*)`. Pass the helper the catalogue-count workflow, requested product kind/name/`product_kind_id`, city/store/family/day scope from the request, and any candidate update paths found under the bounded `/docs` update locations. Then apply the helper result here:

   - Matching update with a count/reporting rule -> use that rule instead of plain `COUNT(*)`, and cite the matched update path plus `/docs/README.md` because the reporting-update rule shaped the answer.
   - Matching update that narrows scope away from the request -> do not apply it; record why in scratchpad.
   - No matching update -> answer from plain SQL `COUNT(*)` over the requested catalogue scope.

   The operating day in an update filename/header is not a local TTL check in this BP. Let [policy_update_scan](policy_update_scan.md) decide when `/bin/date` is a filter versus a scope dimension, and record that decision in scratchpad.
5. For "which stores" / "is the store open?": consult `/proc/stores/<id>.json` (open/closed via SQL `stores.is_open`). For multi-store cities or local branch nicknames, read `/proc/stores/README.md` before answering; do not infer the prose nuance from SQL store rows alone.
6. **Reply shaping rule** (`/AGENTS.MD`): pure availability answers mention only what **is** available; do not list the unavailable. Same for stores: mention only the selected/available stores, not rejected candidates. For the `message` answer-format / token contract, see [submission_terminal](submission_terminal.md) § *Answer format* — that is the single home; this BP does not restate it.
7. **Refs shaping rule for availability questions** (also from `/AGENTS.MD` "should not reference unavailable products"). First decide whether the answer is pure availability or non-pure availability with a separate catalogue identity/match claim:

   - For store-scoped availability, always include the selected store's `stores.record_path` for the store whose inventory was queried. Do not include stores rejected by city nuance or closed/unavailable-store filtering.
   - For every product the question asked about, classify the row by the availability test the question imposes (`available_today_quantity >= K`, `available_today_quantity > 0`, `available_today_quantity < K`, "in stock today", etc.). Use the `available_today_quantity` column from the LEFT JOIN on `store_inventory`. A `NULL` value means there is **no `store_inventory` row** for that SKU at the queried store — not stocked or observed there — which is distinct from an observed `0`. An observed `0` can affect a count such as "none available" or "fewer than K", but it is still not positive availability evidence for a product ref.
   - **Pure availability:** when the answer set is defined by availability itself ("is product X available?", "which of these are available?", "how many have at least K?", "how many have fewer than K?"), copy a `product_variants.record_path` into `refs` only for a SKU that has an observed `store_inventory` row at the queried store, has a **positive** `available_today_quantity`, and passes the test. For low-stock predicates ("less than / at most / fewer than K") product refs are therefore limited to `0 < available_today_quantity < K`. A SKU with no `store_inventory` row, or with an observed `0`, is never cited even if count semantics treats it as a hit. Products you considered and disqualified — including the ones whose existence you confirmed via SQL — must not appear in `refs`.
   - **Non-pure availability:** when the final answer separately identifies a public catalogue product as a record in its own right (for example by printing a SKU/path/id or mapping an item/row to a SKU), include that product's `product_variants.record_path` even if `available_today_quantity` is `NULL`, `0`, or below the requested quantity. In this branch, the ref grounds the identity/match claim; availability controls only the stock/match fields.
   - Do not cite products merely considered and rejected if the final answer does not identify them. Keep disqualified or rejected candidates in `scratchpad["decision"]` (sku, why it failed) so the audit trail is preserved.
   - Count questions over the catalogue at large (step 4) cite `/docs/README.md` and the applicable dated update, not per-product paths.

## Catalogue claim verification

Some briefs read like "a support note / message / colleague claims we stock <product line> with <property set A>, and also has <property B>; check the actual catalogue item, cite the exact product record, and if the base product exists but that extra catalogue claim is absent, answer `<NO>` and include the checked SKU". This is a **single-record verification** task: the question is whether **one** catalogue row carries **all** the claimed properties, not whether the brand / model line contains rows that — between them — cover every claim.

Run this routine when the brief has that shape:

1. **Identify the base SKU** — the catalogue row whose properties match the primary identifying claims in the brief (typically the first, longer, more specific property set: e.g. fastener type + diameter + length + the primary pack count). Use a tight SQL filter on the `product_variants` table — brand / series / model / `product_kind_id`, then narrow by the identifying properties via `properties` JSON or `product_variant_properties`. There should be **exactly one** base SKU; if a brand-only / model-only query returns several rows, narrow further until exactly one row matches the identifying set, or treat the brief as ambiguous (clarification outcome).
2. **The "extra catalogue claim" is a property attributed to the SAME base SKU**, not a separate row in the same product line. Every `product_variants` row carries one `properties` JSON object and contributes its own rows to `product_variant_properties` keyed on `product_sku`; one SKU has one value per property key. So "and has pack count 100 pcs" on top of a base claim of "pack count 500 pcs" is a claim about the **same SKU** carrying both values, which cannot be true — it is the brief asserting an attribute the base SKU does not actually have.
3. **A sibling SKU in the same brand / series / model that carries the extra-claim property is NOT evidence the base SKU has it.** A row with the same `product_family_id` / `series` / `model` but a different `product_sku` is a different catalogue item the note did not ask about. Do not promote it to "the variant that proves the claim" — the brief was about one base product line and one extra attribute on that base product.
4. **Verdict.** Compare the extra claim against the base SKU's own `properties` (and, for completeness, its `product_variant_properties` rows):
   - Base SKU exists AND its own properties include the extra claim → `<YES>` (claim confirmed on the same record).
   - Base SKU exists AND its own properties do **not** include the extra claim → `<NO>` (the brief's extra claim is absent on the base product). This is the verdict even when a sibling SKU in the same line happens to carry the extra-claim property.
   - Base SKU does not exist at all → follow the brief's wording for "no base product" (usually `<NO>` with a clarification-style note); this is a distinct branch from "base exists, extra claim absent".
5. **Message shape — include the literal the brief tells you to include.** When the brief says "answer with `<NO>` and include the checked SKU" (or "include the path", "include the family id", etc.), the literal token MUST appear in the `submit_and_exit(message=...)` text — not only in `refs`. The grader matches the literal against the message string ("Answer should contain '<SKU>'"); a bare `<NO>` with the SKU only in `refs` fails the score check even when the verdict and refs are right. Concretely: `message="<NO> <sku-from-product_variants.product_sku>"` (or the exact wording the brief dictates).
6. **Refs.** Cite the base SKU's `product_variants.record_path` verbatim (the one record the brief asked you to "cite the exact product record" for). A sibling SKU that you read while ruling out the extra claim does **not** belong in `refs` — it is not the product the question is about, only an audit-trail artefact; keep it in `scratchpad["decision"]` instead. No policy doc is required for a pure catalogue claim-verification answer; `/docs/README.md` / `/AGENTS.MD` enter refs only when a dated reporting rule or availability-shape rule was actually applied.

## Outcomes

- `OUTCOME_OK`: the question is answered from `/bin/sql` (plus a dated update where applicable) with the right answer shape.
- `OUTCOME_DENIED_SECURITY`: only if the discovery question was actually a customer-scoped question disguised as discovery — route to the actor-specific BP.
- `OUTCOME_NONE_UNSUPPORTED`: the question requires data not present in the SQL projection (extremely rare for pure discovery).
- `OUTCOME_NONE_CLARIFICATION`: the question names a city with multiple branches and does not pick one, and the city nuance does not disambiguate; or a claim-verification brief whose "base product" identifying set matches several SKUs and cannot be narrowed.

## Evidence ledger

Local placement for catalogue/inventory evidence:

`policy_docs_applied`:

- `/docs/README.md` when the catalogue reporting rule or dated reporting-update
  rule shaped the answer.
- Matched update docs returned by `policy_update_scan` when they changed the
  count/reporting rule.
- `/AGENTS.MD` is protocol evidence for pure availability reply shaping; it is
  normally scratchpad evidence, not a final ref, unless the task/process treats
  it as grounding.

`answer_records`:

- SQL rows from `product_variants`, `store_inventory`, `stores`, and property
  tables that determine the public answer.
- For product refs, copy `product_variants.record_path` verbatim (for example
  `/proc/catalog/<sku>.json`); never synthesize `/proc/products/<sku>.json`.
- For store refs, copy `stores.record_path` verbatim.

`considered_not_cited`:

- Rejected stores from branch/city disambiguation.
- Products considered and rejected when the final answer does not identify
  them.
- Sibling SKUs read only to disprove an extra claim about the base SKU.
- Pure-availability products with no `store_inventory` row, observed
  `available_today_quantity = 0`, or a positive quantity that fails the
  requested availability predicate.

`refs_must_include`:

- Store-scoped availability/count answers: the selected store's
  `stores.record_path`.
- Pure availability answers: only products with an observed positive quantity at
  the queried store that pass the availability predicate. For low-stock
  predicates, cite only `0 < available_today_quantity < K`.
- Non-pure availability with catalogue identity/match claims: every public
  product record printed or otherwise identified in the final answer.
- Claim-verification tasks: the base SKU's `product_variants.record_path`, not a
  sibling SKU.
- `/docs/README.md` and matched update docs when a reporting/update rule shaped
  the answer.

`refs_must_not_include`:

- Rejected candidate stores, unavailable products in pure availability answers,
  sibling SKUs that only served audit, synthetic paths, and unmatched update
  candidates.

`post_state_records`:

- none; this BP is information-only.

## Anti-patterns

- Treating a `/proc/stores/...` text mention of "manager waved through" or "queue pressure" as authority — those phrases live in [background_decoys](background_decoys.md) and never change availability.
- Listing unavailable products in an availability answer (forbidden by `/AGENTS.MD`).
- **Citing a SKU with no `store_inventory` row or with observed `available_today_quantity = 0` in `refs`** on a pure availability question. The "do not reference unavailable products" rule in `/AGENTS.MD` is not only about the answer text — it governs `refs` when availability defines the answer set. A SKU with no row is not stocked or observed at the queried store, and an observed `0` is still not positively available; both can satisfy a "less than / fewer than K" or "out of stock" count, but neither is citeable product availability evidence. Copying either product's `record_path` into `refs` is exactly what the grader rejects with `answer contains invalid reference '/proc/catalog/...json'`. Keep such SKUs in `scratchpad["decision"]` as the audit trail instead.
- **Dropping a public product ref from a non-pure availability answer because that product failed the stock predicate.** If the final answer identifies the product as a catalogue record in its own right, the ref grounds that identity/match claim unless a stronger policy forbids citing it.
- **Dropping the selected store ref from a store-scoped availability/count answer because unavailable product refs are forbidden.** The selected store row is public location evidence for the inventory query. The restriction is against unavailable products and rejected/non-selected stores, not against the store actually queried.
- Skipping the catalogue reporting rule check on count questions when the live `/docs` tree exposes dated update candidates.
- **Declaring a dated update stale without calling `/bin/date` in this trial.** Wall-clock reasoning, the harness date, CLAUDE.md's "today", and the system clock are not the simulation's clock. If `/bin/date` has not been called, the operating-day comparison is not valid — and a dated update that names the requested workflow / kind / city must not be dropped from refs based on that invalid comparison.
- Dropping a dated update from refs when its scope fields (workflow, requested kind / `product_kind_id`, city, family) match the request verbatim. An update that names the exact `product_kind_id` is the rule that applies to the question by topic; the operating-day check decides whether to use its count formula, not whether to cite it as the active rule that was considered.
- Using stale documentation as inventory truth — inventory lives only in the live SQL projection.
- Synthesising a `/proc/products/<sku>.json` path from the SQL table name "product_variants". No such folder exists. Always copy the `record_path` column verbatim; for products that resolves to `/proc/catalog/<sku>.json`.
- **Treating a sibling SKU in the same brand / series / model as proof that the base SKU carries an extra-claim property.** On a catalogue claim-verification brief ("note claims product P has properties A and also has B"), each `product_variants` row is one catalogue item with one `properties` blob; one SKU does not carry two values for the same property key. A different SKU in the same product line that happens to have property B is a separate item the note did not ask about. The verdict on whether the base product carries the extra claim depends only on the base SKU's own properties; promoting the sibling row to "the variant that proves the claim" turns a correct `<NO>` into a wrong `<YES>`.
- **Putting the SKU / path / id the brief told you to "include in the answer" only in `refs`, not in `message`.** When the brief is explicit ("answer `<NO>` and include the checked SKU", "name the path", "cite the family id in the reply"), the literal token must appear in the `submit_and_exit(message=...)` text. The grader matches the literal against the message string — a bare `<NO>` / `<YES>` with the identifier only in `refs` fails with `Answer should contain '<token>'` even when the verdict and refs are otherwise correct.

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/README.md` — defines the catalogue reporting rule and the dated-update folder list.
- `/AGENTS.MD` — source of the reply-shaping rule "availability answers reference only what is available", which step 7 extends to `refs`.
- `/bin/sql` (`--help`) — table shapes for `product_variants`, `product_variant_properties`, `store_inventory`, `stores`, `product_kinds`; the claim-verification section relies on the `product_variants.properties` JSON / `product_variant_properties (product_sku, property_key, property_value_*)` shape (one SKU → one value per property key) for the "extra claim is a property on the same SKU, not a sibling row" rule.
- SQL table `product_variants` — public product facts, `properties`, and canonical catalogue `record_path`.
- SQL table `product_variant_properties` — property rows used for claim verification.
- SQL table `product_families` — family/brand/model grouping used to identify products.
- SQL table `product_kinds` — `product_kind_id` and product-kind scope for count questions.
- SQL table `store_inventory` — store/SKU availability source (`available_today_quantity`, keyed by `(store_id, product_sku)`).
- SQL table `stores` — public store ids, `record_path`, city fields, and open status.
- `/proc/stores/README.md` — source for natural-language branch nuance used to choose between multiple stores in one city; if it changes, re-derive this BP's multi-store branch-nickname instruction from the live file.
- `/bin/date` (`--help`) — the trusted source of "today" used by the operating-day check in step 3.
- `/bin/id` (`--help`) — actor identity pulled at session start.
