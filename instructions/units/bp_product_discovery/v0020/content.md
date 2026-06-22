# Product Discovery and Catalogue

## When this process applies

A question about the catalogue, product properties, brand/series/model, price, fulfillment type, return policy, SKU lookup, store list, or store hours. Also covers **catalogue claim-verification** where a note/message attributes a property set to a product line and asks the actor to confirm or deny it against the live catalogue. Information-only — never mutates. For **branch availability / inventory / stock-count / export** questions, use [availability](availability.md). For "my basket / order / payment", route through [identity_and_auth](identity_and_auth.md) and the relevant action BP.

## Inputs

- Live workspace paths:
  - `/proc/catalog/<brand>/<sku>.json` — product record per `sku`. The cite is the product's live path; do **not** synthesise `/proc/products/<sku>.json`.
  - `/proc/locations/<city>/<store_id>.json` — store record (for store list / open status).
  - `/docs/catalogue-lookup.md` — catalogue resolution policy: "Use product names, hierarchy fields, brands, prices, fulfillment type, return policy, and properties to resolve catalogue requests. If the request does not identify exactly one product, ask for clarification and cite the candidate SKUs you found."
  - `/AGENTS.MD` — the SKU-lookup answer rule and the reply-shaping rule.
- Tools: `/bin/jq` / `/bin/cat` — the source of catalogue and store truth now that `/bin/sql` is unavailable (see [os_tooling_incidents](os_tooling_incidents.md)). `/bin/date` for any operating-day-scoped reporting (see [date_and_time](date_and_time.md)).

**Record shape (from `bin-help/sqlite_schema.txt`).** A catalog record carries `sku`, `name`, `brand`, `category_id`, `kind_id`, `family_id`, `price_cents`, `fulfillment_type`, `return_policy`, and a `properties` JSON object; per-key rows are in `catalog_properties (sku, property_key, value_json/value_text/value_number/value_bool)`. One SKU has exactly one value per property key.

## Process

For catalogue reporting/count update semantics, invoke [policy_update_scan](policy_update_scan.md); it owns bounded dated-update matching and date-scope interpretation.

1. Call `/bin/id` (cheap; also drives "my" handling). Identity is informational here.
2. **SKU / product lookup.** Resolve the request against `/proc/catalog` using name, hierarchy (`category_id` / `kind_id` / `family_id`), brand, price, fulfillment type, return policy, and `properties`. From `/AGENTS.MD`: "For SKU lookups, answer with `OUTCOME_OK` and the SKU only when exactly one product matches. If a request is ambiguous, answer with `OUTCOME_NONE_CLARIFICATION`, ask which product the user meant, and cite every candidate product record." Emit the single SKU as the bare value per [submission_terminal](submission_terminal.md).
3. **Stores / open status.** Read `/proc/locations/<city>/<store_id>.json` (`is_open` for open/closed). For multi-store cities or branch nicknames, disambiguate from the store records' own fields (`name`, `city`, `address_line_1`); there is no separate branch-nuance README. Keep rejected stores out of `refs`.
4. **Availability / stock-count.** Delegate to [availability](availability.md) — branch inventory rows, same-day availability, incoming, and exports live there.
5. **Catalogue counts.** For "how many products of kind X?" invoke [policy_update_scan](policy_update_scan.md) before answering: a matching dated reporting/count update replaces a plain count; otherwise count over the requested catalogue scope read from `/proc/catalog`.
6. **Reply shaping** (`/AGENTS.MD`): when answering about products, quote all matches and relevant references / mentioned SKUs; for the `message` token contract see [submission_terminal](submission_terminal.md) § *Answer format*.

## Catalogue claim verification

Some briefs read like "a note claims we stock <product line> with <property set A>, and also has <property B>; check the actual catalogue item, cite the exact product record, and answer yes/no". This is a **single-record verification**: whether **one** catalogue row carries **all** the claimed properties.

1. **Identify the base SKU** — the catalogue row whose properties match the primary identifying claims (brand / series / model / `kind_id`, then the identifying properties via `properties` / `catalog_properties`). There should be **exactly one**; if several match, narrow further or treat as clarification.
2. **The "extra catalogue claim" is a property attributed to the SAME base SKU**, not a separate row. One SKU has one value per property key, so "and has pack count 100" on top of a base "pack count 500" is the brief asserting an attribute the base SKU does not have.
3. **A sibling SKU in the same brand / series / model that carries the extra-claim property is NOT evidence the base SKU has it.** It is a different catalogue item the note did not ask about.
4. **Verdict** against the base SKU's own `properties`:
   - Base SKU exists AND includes the extra claim → yes.
   - Base SKU exists AND does **not** include the extra claim → no (even when a sibling SKU carries it).
   - Base SKU does not exist → follow the brief's "no base product" wording.
5. **Message shape.** Emit the yes/no token per [submission_terminal](submission_terminal.md) (read the literal from the live `/AGENTS.MD`). When the brief says "include the checked SKU" (or the path / family id), the literal token MUST appear in `submit_and_exit(message=...)`, not only in `refs` — the grader matches the literal against the message string.
6. **Refs.** Cite the base SKU's `/proc/catalog/<brand>/<sku>.json` (the one record the brief asked you to cite). A sibling SKU read while ruling out the extra claim does **not** belong in `refs` — keep it in `scratchpad["decision"]`.

## Outcomes

- `OUTCOME_OK`: the question is answered from `/proc/catalog` (plus a dated update where applicable) with the right answer shape.
- `OUTCOME_DENIED_SECURITY`: only if the question was actually a customer-scoped action disguised as discovery — route to the actor-specific BP.
- `OUTCOME_NONE_UNSUPPORTED`: the question requires data not in the `/proc` projection.
- `OUTCOME_NONE_CLARIFICATION`: a SKU lookup or claim-verification base set matches several products and cannot be narrowed; or a multi-branch city that cannot be disambiguated.

## Refs to set in scratchpad

- For a product cite: the product's live `/proc/catalog/<brand>/<sku>.json` path. Do NOT synthesise `/proc/products/<sku>.json`.
- For a store cite: the store's live `/proc/locations/<city>/<store_id>.json` path.
- SKU-lookup ambiguity: cite every candidate product record (per `/AGENTS.MD`).
- Claim verification: include only the base SKU's record (not a sibling read while ruling out the extra claim).
- For availability questions, follow [availability](availability.md)'s refs rules.
- A matching dated reporting/count update returned by [policy_update_scan](policy_update_scan.md) when it shaped the answer.

## Anti-patterns

- Synthesising `/proc/products/<sku>.json` from a table name — products live under `/proc/catalog/<brand>/<sku>.json`. Cite the live path you read.
- Returning a SKU on an ambiguous lookup instead of `OUTCOME_NONE_CLARIFICATION` with every candidate cited.
- Treating a sibling SKU in the same line as proof the base SKU carries an extra-claim property (turns a correct "no" into a wrong "yes").
- Putting the SKU/path/id the brief told you to "include in the answer" only in `refs`, not in `message`.
- Emitting a yes/no answer in any token other than the one the live `/AGENTS.MD` specifies (see [submission_terminal](submission_terminal.md)) — read the live token rather than assuming `<YES>`/`<NO>` or a remembered literal.
- Using a background doc (brand, history, expansion) as catalogue or store truth. See [background_decoys](background_decoys.md).
- Trying `/bin/sql` for catalogue/store data — it is down; read `/proc/catalog` and `/proc/locations` JSON.
- Answering branch availability/stock here instead of delegating to [availability](availability.md).

## Dependencies

> If any of these documents change in the live workspace, this BP file may have become stale and must be re-derived.

- `/docs/catalogue-lookup.md` — catalogue resolution rule (resolve to exactly one product; otherwise clarify and cite candidate SKUs). Replaces the removed `/docs/README.md` catalogue reporting rule.
- `/AGENTS.MD` — the SKU-lookup answer rule and the "quote all matches and references" reply-shaping rule.
- `bin-help/sqlite_schema.txt` — `catalog` / `catalog_properties` shape (one value per property key) underpinning claim verification; `locations` for stores.
- `bin-help/jq.help.txt`, `bin-help/cat.help.txt` — JSON read tools used now that `/bin/sql` is unavailable.
- `sql_table catalog` — product facts, `properties`, hierarchy ids, and canonical catalogue path.
- `sql_table catalog_properties` — property rows used for claim verification.
- `sql_table locations` — public store ids, `record_path`, city fields, and `is_open`.
- `/bin/date` (`--help`) — operating-day source for any dated reporting rule.
- `/bin/id` (`--help`) — actor identity pulled at session start.
