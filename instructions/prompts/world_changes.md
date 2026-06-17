# World changes — last accepted baseline → current live world

Triage index for everything that changed between the last accepted world
baseline and the current live workspace. Read it FIRST, then open only what you
need. The PA reads the whole live workspace anyway — this is an attention
director, not a dump.

How to read each section:

- **Content edits** — the rule-bearing deltas. A row marked **in patch** is a
  *surgical* change (a few lines, a flipped word, a changed number); its hunk is
  inlined in [world-edits.patch](world-edits.patch) — read the hunk, it pinpoints
  exactly what changed. A row marked **read live** changed too much for a delta
  to help (effectively a rewrite): open the file at its path and re-derive from
  the current content; do not look for its delta in the patch.
- **Moved** — byte-identical content at a new path (pure rename). Rewrite the
  old path to the new one everywhere a BP names it (including `dependencies`);
  the content did not change, so do not re-derive. NOT in the patch.
- **New files** — no baseline counterpart. May introduce a policy, tool, or
  domain that older BPs cannot know about (a candidate for a *new* BP). Read it
  live and treat what you find as the source of truth. NOT in the patch.
- **Removed** — gone from the live world; anything that leans on it is stale for
  that part.
- **Ambiguous** — identical content at several candidate paths; pick by context.

The **grounds units** column lists the BP units that currently pin that path as
a dependency — the units a change there most likely affects. `—` means no
registered BP depends on it today (often background/decoy docs — lower priority;
but a brand-new file may still warrant a new BP).

Paths are shown as the agent sees them live (`/docs/...`, `/bin/...`);
`bin-help/...` entries are the captured `--help` output of the named
`/bin/<tool>`. The machine-readable file-set map (renames/new/removed) is in
`relocations.json`.

## Content edits

{{EDITS}}

## Moved (identical content, new path)

{{MOVED}}

## New files (read live)

{{NEW}}

## Removed

{{REMOVED}}

## Ambiguous (same content at several candidate paths)

{{AMBIGUOUS}}
