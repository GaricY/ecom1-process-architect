# Product Discovery and Catalogue Lookup

## When this process applies

A catalogue question: "which product / which SKU is this?", product properties, brand/model/family identity, fulfillment type, return policy, a **product existence / match / count query** ("does a product matching <all these specs> exist?", "is there a product that …?", or "**how many** SKUs match <all these specs>?" — a yes/no verdict or a count over the whole requested spec treated as one conjunction of filters), or a **catalogue claim-verification** ("a note claims product P has properties A and also B — check the catalogue and cite the exact record"). Also **comparison-against-an-input**: the task hands you a receipt / OCR / invoice / report and asks you to compare today's catalogue prices or properties against it. Information-only — never mutates. For "is X available today at Y" / stock-count / inventory, route to [availability_and_inventory](availability_and_inventory.md). For "my basket / order / payment", route through [identity_and_auth](identity_and_auth.md) and the relevant action BP.

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
4. Record the domain verdict and any required identifier/path payload; [submission_terminal](submission_terminal.md) owns the final answer formatting (bare SKU, yes/no `TRUE(1)`/`FALSE(0)`, number, prose).

### Product existence / match / count query

"Does such a product exist?", "is there a product that matches <all these specs>?", "do we sell a <full spec>?", or "**how many** SKUs match <all these specs>?" — the whole requested description is one conjunction of filters, and the answer (a yes/no verdict, or a count) is how many records satisfy it. The brief does **not** pre-name one product to cite; every descriptor (brand, kind, kit, each property such as a `battery_platform`, a price ceiling, an exclusion such as "without accessory bundle/set") is part of the search filter, not a separate "base product + extra claim".

1. Narrow `/proc/catalog` candidates and read them. A record is a **match** only when its own fields/`properties` satisfy **every** requested spec at once — each property predicate, a price ceiling against `price_cents`, and an exclusion against `name`/`properties` (an "accessory set/bundle" record fails "without accessory bundle"). An attribute the request did **not** supply is **not** a filter — do not invent one (e.g. an unsupplied tank size excludes nothing).
2. Verdict: existence → some record matches all specs → exists, none → does not exist; count → the **number** of records that satisfy every filter. A record that matches most descriptors but fails even one requested spec (a different `battery_platform`, over the price ceiling, an accessory set when the bundle is excluded) is a **rejected near-miss**, not a match. [submission_terminal](submission_terminal.md) shapes the yes/no `TRUE(1)`/`FALSE(0)` token or the "number only" answer.
3. Refs are **exactly the surviving cohort** — the live `/proc/catalog/...json` paths of the records that satisfy every spec (the full matches that make up the count), and only those. A near-miss / filter-excluded record stays in `scratchpad` as `considered_not_cited`, exactly as a disqualified product is never cited on availability; never promote it to a ref because it carried most of the requested specs. On a "does not exist" / zero-count answer **cite nothing**.
4. This is **not** the clarification branch: the filters are explicit, so excluded candidates are *rejected*, not unresolved ambiguous candidates — do not fall back to "cite every candidate".

### Catalogue claim verification

A single-record verification of a **pre-identified** product: a note names product P (and asks you to "cite the exact record") and you check whether that **one** catalogue row carries **all** the claimed properties. An open "does such a product exist / how many match all of <spec>" question is instead a *Product existence / match / count query* (above), where a near-miss / filter-excluded record is not cited.

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

- `OUTCOME_OK`: the catalogue question is answered with the right shape (exactly-one SKU, existence yes/no, match count, claim verdict, comparison result).
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
- On an existence / match / count query, only the `/proc/catalog` records that satisfy **every** requested spec (the cohort that makes up the count); a "does not exist" / zero-count verdict has no answer record.

`considered_not_cited`:

- Products considered and rejected when the final answer does not identify them; sibling SKUs read only to disprove an extra claim.
- Near-miss / filter-excluded records that fail one or more requested specs (a property, a price ceiling, an exclusion) on an existence / match / count query.

`refs_must_include`:

- The matched base SKU's `/proc/catalog/...json` on claim verification.
- On an existence / match / count query, every `/proc/catalog/...json` that satisfies all requested specs (the full-match cohort that makes up the count), and only those.
- Every candidate `/proc/catalog/...json` on `OUTCOME_NONE_CLARIFICATION`.
- The request-named input artifact path on comparison answers, plus the catalogue records compared against.

`refs_must_not_include`:

- Sibling SKUs that only served audit; rejected candidates; synthesised paths.
- Near-miss / filter-excluded `/proc/catalog` records that fail a requested spec (property, price ceiling, or exclusion) on an existence / match / count query (a "does not exist" / zero-count verdict cites no catalogue record).

`post_state_records`:

- none; this BP is information-only.

## Anti-patterns

- Answering `OUTCOME_OK` with a SKU when more than one product matches — `/AGENTS.MD` requires exactly one match; otherwise clarify and cite candidates.
- Citing a near-miss / filter-excluded `/proc/catalog` record on an existence / "how many match?" query — only records satisfying **every** requested spec (the cohort that makes up the count) are cited; a price- or bundle-excluded candidate, or a near-miss read to disprove existence, stays in scratchpad. A "does not exist" / zero-count answer cites no catalogue record. This differs from claim verification (brief pre-names one product, cite that exact record) and from clarification (filters here are explicit, so excluded candidates are rejected, not "cite every candidate").
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
- `catalog` (`/proc/catalog`) — product `sku`, `name`, hierarchy ids, `brand`, `price_cents`, `fulfillment_type`, `return_policy`, and `properties` used to identify products, apply existence/count filter predicates, and verify claims.
- `/bin/id` (`--help`) — actor identity pulled at session start.
