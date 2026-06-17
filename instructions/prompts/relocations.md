# File-set changes — SHA256 map (last accepted baseline → current live world)

Every entry below compares the **last accepted world baseline** with the
**current live workspace**. A content **SHA256** that appears at two different
paths proves it is the *same* file that merely **moved**. A path present on only
one side that has no hash twin but is *highly similar* to a one-sided path on the
other side was likely **renamed and edited**. A one-sided path with neither is a
genuine **new** or **removed** file. Content edits to a file that keeps its path
are not listed here — those surface as ordinary diffs.

How to read each section:

- **Moved** — byte-identical content at a new path. Read the file at its new
  path; do not treat it as missing and do not re-derive its meaning — the
  content did not change. (These moves account for most of the bulk in any
  accompanying `*-diff.patch`: the delete-half and add-half of each rename.)
- **Renamed & changed** — a removed path and an added path matched by high token
  similarity: almost certainly the *same* document, renamed AND edited. Treat
  the location like a move (rewrite references from the old path to the new one),
  but because the content also changed, re-derive anything that depended on it
  from the **new** path — do not assume the old wording survived.
- **New files** — a path with no counterpart in the baseline. It may introduce a
  policy, tool, or domain that older process descriptions cannot know about.
  Read it live and treat what you find as the source of truth.
- **Removed** — a path the baseline had and the live world no longer does.
  Anything that leans on it is stale for that part; confirm against the live
  world before acting on it.

Paths are shown as the agent sees them live (`/docs/...`, `/bin/...`);
`bin-help/...` entries are the captured `--help` output of the named
`/bin/<tool>`.

## Moved (same content, new path)

{{MOVED}}

## Renamed & changed (likely the same document at a new path — content also edited)

{{RENAMED_CHANGED}}

## Ambiguous (same content at several candidate paths — choose by context)

{{AMBIGUOUS}}

## New files

{{ADDED}}

## Removed

{{REMOVED}}
