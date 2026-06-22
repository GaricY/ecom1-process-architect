# Product Discovery and Catalogue Lookup

## When this process applies

A catalogue question: "which product / which SKU is this?", product properties, brand/model/family identity, fulfillment type, return policy, or a **catalogue claim-verification** ("a note claims product P has properties A and also B — check the catalogue and cite the exact record"). Also **comparison-against-an-input**: the task hands you a receipt / OCR / invoice / report and asks you to compare today's catalogue prices or properties against it. Information-only — never mutates. For "is X available today at Y" / stock-count / inventory, route to [availability_and_inventory](availability_and_inventory.md). For "my basket / order / payment", route through [identity_and_auth](identity_and_auth.md) and the relevant action BP.

## Inputs

- Live workspace paths:
  - `/proc/catalog/<...>.json` — product records. Fields: `id`, `sku`, `name`, `brand`, `category_id`, `kind_id`, `family_id`, `price_cents`, `fulfillment_type`, `return_policy`, `properties` (object). The cite path is the live `/proc/catalog/...json` path you read; never synthesise from a SKU.
  - `/docs/catalogue-lookup.md` — how to resolve catalogue requests and the clarification rule.
  - `/docs/attachments.md` — `/uploads` is the upload root for receipts/OCR/documents, which are cross-checked against canonical catalogue records.
  - `/AGENTS.MD` — SKU-lookup answer rule and the yes/no token.
  - Request-named input artifacts under `/uploads` the task points to.
- Tools: `/bin/id` (identity, also drives "my" handling); `/bin/cat` / `/bin/jq` to read records. SQL is unavailable — discover with `ws.find`/`ws.list` under `/proc/catalog` and read JSON.

## Process

1. Call `/bin/id` (cheap; discovery answers do not depend on actor).
2. Resolve the product from `/docs/catalogue-lookup.md`: use product `name`, hierarchy fields (`category_id`/`kind_id`/`family_id`), `brand`, `price_cents`, `fulfillment_type`, `return_policy`, and `properties`. Narrow `ws.find`/`ws.list` results to candidate `/proc/catalog` records and read them.
3. **SKU lookup answer rule (`/AGENTS.MD`).** Answer `OUTCOME_OK` with the SKU only when **exactly one** product matches. If the request is ambiguous, answer `OUTCOME_NONE_CLARIFICATION`, ask which product is meant, and cite **every** candidate product record. From `/docs/catalogue-lookup.md`: "When user talks about products - quote all matches and relevant references, mentioned SKUs."
4. Record the domain verdict and any required identifier/path payload; [submission_terminal](submission_terminal.md) owns the final answer formatting (bare SKU, yes/no `TRUE(1)`/`FALSE(0)`, prose).

### Catalogue claim verification

A single-record verification: does **one** catalogue row carry **all** the claimed properties?

1. Identify the base SKU — the `/proc/catalog` row matching the primary identifying claims (narrow by brand / series / model / `kind_id`, then by the identifying `properties`). There should be exactly one; if several match and you cannot narrow, treat as ambiguous (clarification).
2. The "extra claim" is a property attributed to the **same** base SKU. Each catalog record has one `properties` object — one value per key. A claim that the base SKU has two values for one property (e.g. pack count 500 and also 100) cannot be true.
3. A sibling SKU in the same brand/series/model that carries the extra property is **not** evidence the base SKU has it — it is a different product the note did not ask about.
4. Verdict: base SKU's own `properties` include the extra claim → confirmed; do not include → negative (even if a sibling carries it); base SKU absent → follow the brief's "no base product" branch.
5. If the brief says to include the checked SKU/path/id in the answer, record it as a required `message` payload element (not refs-only).
6. Refs: cite the base SKU's live `/proc/catalog/...json` path; a sibling read only to rule out the claim stays in scratchpad.

### Comparison against a handed-in input document

1. Read the input artifact live (under `/uploads`) and derive its baseline facts (old prices, quantities, listed items). Keep its absolute live path.
2. Map each line to the live catalogue via `/proc/catalog` reads; compute the comparison from the input's baseline against current `price_cents`/`properties`.
3. The input artifact's own live path is a **required ref** — the answer's baseline came from it (`/docs/attachments.md`: uploads are evidence for the artifact itself, cross-checked against canonical records). Cite it alongside the catalogue records, unless [privacy_and_disclosure](privacy_and_disclosure.md) forbids it. Pasted task text has no live path.

## Outcomes

- `OUTCOME_OK`: the catalogue question is answered with the right shape (exactly-one SKU, claim verdict, comparison result).
- `OUTCOME_NONE_CLARIFICATION`: the request matches several SKUs and cannot be narrowed; cite every candidate.
- `OUTCOME_NONE_UNSUPPORTED`: the question needs data not present in the catalogue (rare), or asks for a mutation this BP does not own.
- `OUTCOME_DENIED_SECURITY`: only if a "discovery" question was actually a customer-scoped action disguised as discovery — route to the actor-specific BP.

## Evidence ledger

`request_named_inputs`:

- Any `/uploads` artifact the task handed you to compare/verify against. Its absolute live path is load-bearing answer evidence, not just a `read_set` entry.

`policy_docs_applied`:

- `/docs/catalogue-lookup.md` when its resolution/clarification rule shaped the answer.
- `/AGENTS.MD` is protocol evidence for the SKU/clarification/yes-no shaping; normally scratchpad, a final ref only when treated as grounding.

`answer_records`:

- `/proc/catalog` records that determine the answer; copy the live read path verbatim.

`considered_not_cited`:

- Products considered and rejected when the final answer does not identify them; sibling SKUs read only to disprove an extra claim.

`refs_must_include`:

- The matched base SKU's `/proc/catalog/...json` on claim verification.
- Every candidate `/proc/catalog/...json` on `OUTCOME_NONE_CLARIFICATION`.
- The request-named input artifact path on comparison answers, plus the catalogue records compared against.

`refs_must_not_include`:

- Sibling SKUs that only served audit; rejected candidates; synthesised paths.

`post_state_records`:

- none; this BP is information-only.

## Anti-patterns

- Answering `OUTCOME_OK` with a SKU when more than one product matches — `/AGENTS.MD` requires exactly one match; otherwise clarify and cite candidates.
- Synthesising a `/proc/catalog/<sku>.json` path from a SKU instead of copying the live read path.
- Treating a sibling SKU in the same brand/series/model as proof the base SKU carries an extra-claim property.
- Putting a SKU/path/id the brief told you to include only in `refs`, not in `message`.
- Comparing against a handed-in input and citing only the catalogue records, dropping the input file's own live path.
- Answering availability/stock from this BP — route to [availability_and_inventory](availability_and_inventory.md).

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/catalogue-lookup.md` — catalogue resolution fields and the "ask for clarification, cite candidate SKUs" rule.
- `/docs/attachments.md` — `/uploads` as the input root and the cross-check-against-canonical-records rule.
- `/AGENTS.MD` — the SKU-lookup answer rule and the yes/no token.
- `catalog` (`/proc/catalog`) — product `sku`, `name`, hierarchy ids, `brand`, `price_cents`, `fulfillment_type`, `return_policy`, and `properties` used to identify products and verify claims.
- `/bin/id` (`--help`) — actor identity pulled at session start.
