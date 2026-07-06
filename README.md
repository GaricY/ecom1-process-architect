# Process Architect: Business Process Map as Code

## Glossary and Repository Map

This README is the entry point. It explains the competition context, the results, and the main idea behind the project. Details are split across dedicated documents and artifacts:

- **World**: documents, tools, state, and DB schema for a specific BitGN run.
- **Executor**: the execution agent that solves a task using the rendered operating manual.
- **Process Architect / PA**: the architect agent that analyzes failures and world drift, then publishes new process versions.
- **Unit / business process**: an immutable version of an instruction for a specific class of operations: checkout, returns, fraud review, and so on.
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: the Process Architect internals: Instruction Store, Resolver, world drift handling, PA loop, and task lifecycle.
- **[OPERATING.md](OPERATING.md)**: the operating runbook: startup, environment variables, and modes.
- **`runs/`**: published run artifacts. `*.html` files are overview reports for run series, `*.png` files are leaderboard/eval screenshots, and `*.tar.gz` files are `task_dir` archives with `task.md`, `answer.json`, `result.json`, world dumps (`vault/`, `bin-help/`), attention packages, and Executor logs (`.logs/`, `instruction-selection.json`, `execute_python`).

Repository branches:

- **`competition-blind`**: the version used in the main blind competition.
- **`postmortem-dev`**: refactoring and fixes in the DEV environment.
- **`postmortem-prod`**: postmortem validation of fixes on the PROD world, evolution branch.

## About the Competition

**BitGN Agent Challenge** is a series of competitions where autonomous agents solve tasks inside deterministic simulations of real businesses. The **ECOM1** release focuses on the operational layer of an online store: the agent does not "chat about products"; it does the store's work. It handles fuzzy product searches, builds baskets, performs checkout, recovers payments after 3DS failures, handles returns, calculates inventory, catches fraudulent payments, and attaches **evidence references** to every answer.

The environment is a small Unix-like system. Everything needed is available at its top level:

- `/AGENTS.md`: local rules for a specific run, down to the exact words to use for "yes" and "no";
- `/docs`: policies: security, discounts, returns, payment recovery;
- `/proc`: current world state: products, stores, employees, baskets, payments;
- `/bin`: allowed command-line utilities that the agent uses to act and verify facts. `/bin/checkout` checks out a basket, `/bin/id` reports who the request is made on behalf of (needed for permission and ownership checks), and `/bin/sql` runs queries against the store database.

The final `answer` call accepts not only a user-facing message but also a machine-readable **outcome** (`OK`, security denial, clarification request, unsupported operation) and a list of **evidence references**. The grader strictly evaluates observable behavior: which actions were performed, which state changes were recorded, whether the correct evidence was attached, and whether the exact response format was followed. Text polish is not graded, but one extra or missing reference can zero out the whole task.

**What tasks look like.** Requests arrive in human language: often casual, sometimes adversarial. Two real examples from the blind PROD run:

*1. Fuzzy availability request:*

> Do you have 8 of 'bosch gex 125 accessory set with discs' (but not PT-SND-BOS-GEX125-DUST) in stock in alpenstrasse tools place?

One sentence contains a fuzzy product name, an exclusion (`but not ...`), a fuzzy store name, and a quantity threshold. The agent finds the right SKU and store, calculates availability, and answers in the format defined by `/AGENTS.md`.
**Answer:** outcome `OK` / `FALSE(2)` (no; only 2 available) / evidence: store record, product card, `/docs/availability-checks.md`.

*2. OCR scan to working artifact:*

> Read the uploaded competitor purchase request OCR at /uploads/[redacted]_ocr.txt and create a TSV crosslist report at /exports/crosslist-[redacted].tsv.

The input is a noisy scan of a competitor's purchase request: line items are written using the competitor's codes and terms, not ours. Following `/docs/purchase-request-crosslist.md`, the agent identifies the store branch, maps each line item to our SKU, and writes the finished TSV report.
**Answer:** outcome `OK` / path `/exports/crosslist-[redacted].tsv` / evidence: OCR file, crosslist policy, store record, and matched product cards.

**How the competition works.** There are two environments. In **DEV**, we prepare the agent: run tasks, inspect traces, and fix logic. Importantly, **DEV exposes the score**: the grader evaluates each task, providing a signal to evolve against. During the process, the organizer adds new tasks and adjusts the world. This is the main trap: it is easy to overfit the agent to specific DEV products, baskets, and filenames, and fail later as a result. The official score is measured during the **blind PROD window**. "Blind" means exactly that: PROD is not visible ahead of time, and the run itself has **no score**. The grader is silent; there is no task-level feedback. The world may differ radically: different task texts, different state structures, renamed policy files, different table columns. Only a few things are guaranteed: it is still e-commerce, and it will still have `AGENTS.md` and `/bin`.

## Results: Leaderboard + Postmortem Fixes

**Official result:** 11th place in the Hall of Fame: [Accuracy](https://bitgn.com/l/ecom1-accuracy); **15th place** in the overall [Ultimate](https://bitgn.com/l/ecom1-ultimate) ranking.

![Hall of Fame: Accuracy, @GaricY Process Architect - 11th place, 73.2/100](runs/hall-of-fame-accuracy.png)

After the contest, postmortem fixes improved the dev-to-prod adaptation.

![Postmortem DEV: 54.8/55](runs/postmortem-dev.png)

![Postmortem PROD: 0.81 across 100 trials](runs/postmortem-prod.png)

After one round of process evolution, the system reached more than 90%.

![Postmortem PROD eval: 93.5/100](runs/postmortem-prod-eval.png)

## Idea: Business Processes as Code

I spent more than 15 years implementing ERP systems, and every project starts the same way. What do we start with? ~~We sit down and write code.~~ We **map the business processes.** Code comes later; it is only one way to express a process that already exists in policies, in people's heads, and in how the business actually works.

Designing complex AI agents seems to run into a similar problem. If an agent's instructions grow as one giant monolith, they quickly become brittle and hard to maintain.

> **The main idea in plain terms:**
> Stability through decomposition. The agent's instructions are split into independent processes with minimal dependencies. When the "live world" changes (rules, utilities, DB schemas), Executor does not break: it receives a precise diff of the mismatches and adapts on the fly. Meanwhile, Process Architect designs and publishes new versions of stale units.

This leads to three key differences in Process Architect:

- **Agent instructions are code.** The operating manual consists of modular, versioned, immutable units (business processes).
- **The domain is outside the framework.** The orchestrator, Instruction Store, and architect loop know nothing about e-commerce. The agent derives domain knowledge from the live world on its own. Point the same machine at another business, and it will design a new process map.
- **The business domain comes first; task scenarios come second.** When building the initial process map, I do not try to guess which exact requests the agent will receive. The base manual is built entirely around the enterprise itself and its policies (e.g., how a basket works, how a return is processed). A process describes how the business works, not how to solve a specific test. Later, the system adapts to the specifics of real incoming tasks naturally through unit evolution.

## Contacts

- Igor Lasiychuk
- Telegram: @GaricY
- ECOM1 demo site: [site/](site/)
- LinkedIn: https://www.linkedin.com/in/igor-lasiychuk/
