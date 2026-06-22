"""Workspace client used by every `execute_python` snippet.

Wraps the BitGN ECOM runtime ConnectRPC client and exposes a single tidy
surface for the agent:

    ws.tree(...), ws.list(...), ws.read(...), ws.read_json(...),
    ws.search(...), ws.find(...), ws.stat(...), ws.proc(...), ws.jq(...),
    ws.sql(...), ws.exec_tool(...), ws.date(), ws.id(),
    ws.answer(scratchpad, verify), ws.write(...), ws.delete(...)

`submit_and_exit(...)` is exposed at the prelude level on top of `ws.answer`
and is the preferred way to finish a task — it merges scratchpad fields,
writes `answer.json`, and exits the snippet with SystemExit(0).

The harness URL is taken from `RUNTIME_HARNESS_URL` in the subprocess
environment. The orchestrator's MCP server sets it just for the subprocess
that runs the snippet; the Claude CLI process and the task directory never
see it.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import time
from pathlib import Path
from typing import Iterable

from bitgn.vm.ecom.ecom_connect import EcomRuntimeClientSync
from bitgn.vm.ecom.ecom_pb2 import (
    AnswerRequest,
    DeleteRequest,
    ExecRequest,
    FindRequest,
    ListRequest,
    NodeKind,
    Outcome,
    ReadRequest,
    SearchRequest,
    StatRequest,
    TreeRequest,
    WriteRequest,
)
from google.protobuf.json_format import MessageToDict

# Retry layer for every harness RPC. The runtime client has no built-in
# retries, so a transient blip would otherwise surface as an exception
# inside an `execute_python` snippet and burn an agent turn.
_VM_RETRY_ATTEMPTS = 5
_VM_RETRY_BACKOFF_SEC = 0.2


class _RetryingClient:
    """Proxy that retries every callable method on exception."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def __getattr__(self, name: str):
        attr = getattr(self._inner, name)
        if not callable(attr):
            return attr

        def wrapped(*args, **kwargs):
            last_exc = None
            for attempt in range(_VM_RETRY_ATTEMPTS):
                try:
                    return attr(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < _VM_RETRY_ATTEMPTS - 1:
                        time.sleep(_VM_RETRY_BACKOFF_SEC * (attempt + 1))
            assert last_exc is not None
            raise last_exc

        return wrapped


_ENV_HARNESS_URL = "RUNTIME_HARNESS_URL"
_ENV_ANSWER_PATH = "ECOM_ANSWER_PATH"
_ENV_TOOL_CALLS_PATH = "ECOM_TOOL_CALLS_PATH"

_KIND_MAP = {
    "all": NodeKind.NODE_KIND_UNSPECIFIED,
    "files": NodeKind.NODE_KIND_FILE,
    "dirs": NodeKind.NODE_KIND_DIR,
}

_OUTCOME_MAP = {
    "OUTCOME_OK": Outcome.OUTCOME_OK,
    "OUTCOME_DENIED_SECURITY": Outcome.OUTCOME_DENIED_SECURITY,
    "OUTCOME_NONE_CLARIFICATION": Outcome.OUTCOME_NONE_CLARIFICATION,
    "OUTCOME_NONE_UNSUPPORTED": Outcome.OUTCOME_NONE_UNSUPPORTED,
    "OUTCOME_ERR_INTERNAL": Outcome.OUTCOME_ERR_INTERNAL,
}


def _to_dict(msg) -> dict:
    # always_print_fields_with_no_presence=True keeps default-valued scalars
    # in the dict (e.g. exit_code=0, stdout=""), so callers can rely on
    # res["exit_code"] / res["stdout"] without KeyError on success.
    return MessageToDict(
        msg,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True,
    )


class Workspace:
    def __init__(
        self,
        harness_url: str | None = None,
        answer_path: str | None = None,
        tool_calls_path: str | None = None,
    ) -> None:
        url = harness_url or os.environ.get(_ENV_HARNESS_URL)
        if not url:
            raise RuntimeError(
                f"{_ENV_HARNESS_URL} is not set — Workspace can only be used "
                "inside an execute_python subprocess spawned by the MCP server."
            )
        self._answer_path = answer_path or os.environ.get(_ENV_ANSWER_PATH) or ""
        if not self._answer_path:
            raise RuntimeError(f"{_ENV_ANSWER_PATH} is not set")
        self._vm = _RetryingClient(EcomRuntimeClientSync(url))
        self._tool_calls_path = (
            tool_calls_path or os.environ.get(_ENV_TOOL_CALLS_PATH) or ""
        )

    # ── audit ─────────────────────────────────────────────────────────────
    def _audit(
        self,
        tool: str,
        payload: dict,
        response: dict | None = None,
    ) -> None:
        if not self._tool_calls_path:
            return
        try:
            entry = {"tool": tool, **payload}
            if response is not None:
                entry["response"] = response
            with open(self._tool_calls_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass

    # ── filesystem reads ──────────────────────────────────────────────────
    def tree(self, root: str = "", level: int = 2) -> dict:
        self._audit("tree", {"root": root, "level": level})
        return _to_dict(self._vm.tree(TreeRequest(root=root, level=level)))

    def list(self, path: str = "/") -> dict:
        self._audit("list", {"path": path})
        return _to_dict(self._vm.list(ListRequest(path=path)))

    def find(
        self,
        root: str = "/",
        name: str = "",
        kind: str = "all",
        limit: int = 10,
    ) -> dict:
        self._audit("find", {"root": root, "name": name, "kind": kind, "limit": limit})
        return _to_dict(
            self._vm.find(
                FindRequest(root=root, name=name, kind=_KIND_MAP[kind], limit=limit)
            )
        )

    def search(self, root: str = "/", pattern: str = "", limit: int = 10) -> dict:
        self._audit("search", {"root": root, "pattern": pattern, "limit": limit})
        return _to_dict(
            self._vm.search(SearchRequest(root=root, pattern=pattern, limit=limit))
        )

    def stat(self, path: str) -> dict:
        self._audit("stat", {"path": path})
        return _to_dict(self._vm.stat(StatRequest(path=path)))

    def read(
        self,
        path: str,
        number: bool = False,
        start_line: int = 0,
        end_line: int = 0,
    ) -> dict:
        # Audit AFTER the RPC so PA can replay /proc/<...> records from the
        # response payload (Process Architect uses this to rebuild vault/proc/
        # in its workdir — see orchestrator.instructions.pa_workdir).
        response = _to_dict(
            self._vm.read(
                ReadRequest(
                    path=path,
                    number=number,
                    start_line=start_line,
                    end_line=end_line,
                )
            )
        )
        self._audit(
            "read",
            {"path": path, "number": number, "start_line": start_line, "end_line": end_line},
            response=response,
        )
        return response

    def read_json(self, path: str) -> dict:
        """`ws.read` + `json.loads`, with `record_path` injected.

        The warehouse is a file-shaped JSON projection under `/proc/...`
        (the primary way to read it while `/bin/sql` is down). This removes
        the easy-to-drop `json.loads(ws.read(path)["content"])` boilerplate
        and fails loudly on truncation or invalid JSON instead of returning
        a half-parsed record.

        Returns the parsed object. For a dict record the absolute `path` is
        stored under `record_path` (without clobbering a real field) so you
        can cite it directly in refs.
        """
        res = self.read(path)
        if res.get("truncated"):
            raise RuntimeError(
                f"ws.read_json: {path} was truncated by the read RPC; "
                "re-read in line ranges and assemble the JSON yourself."
            )
        content = res.get("content", "")
        try:
            obj = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"ws.read_json: {path} is not valid JSON: {exc}; "
                f"head={content[:200]!r}"
            ) from exc
        if isinstance(obj, dict):
            obj.setdefault("record_path", path)
        return obj

    def proc(self, family: str, scope: str = "", *, limit: int = 5000) -> dict:
        """Load every JSON record under a `/proc` family as parsed dicts.

        Since `/bin/sql` went down the warehouse is served as a file-shaped
        projection: `/proc/<family>/<partition>/<id>.json`. This is the
        bulk-scan primitive — the replacement for `SELECT * FROM <table>`
        for whole-family work (aggregations, joins). For a single known
        record use `ws.read_json`; to narrow first use `ws.search` (content)
        or `ws.find` (path glob), then `ws.read_json` the hits.

        `family` — a `/proc` family name (`"catalog"`, `"carts"`, ...) or a
                   full `/proc/...` root. **Family names can differ per
                   trial** (the runtime relocates them, e.g. `stores` vs
                   `locations`, `returns` vs `return-workflows`) — list
                   `/proc` live to see this trial's names, do not assume.
        `scope`  — optional partition subdir to narrow the scan (a customer
                   id, brand, city, store id — the first segment under the
                   family).

        Returns `{"records": [ {<fields...>, "record_path": "/proc/..."} ],
        "count": int, "truncated": bool}`. Each record carries its absolute
        `record_path` — cite that in refs.

        Reads go through `ws.read` (audited WITH the response payload) so the
        Process Architect can still rebuild `vault/proc/` from the trace. Do
        not reroute this through `/bin/cat`.
        """
        root = family if family.startswith("/") else f"/proc/{family.strip('/')}"
        if scope:
            root = f"{root.rstrip('/')}/{scope.strip('/')}"
        try:
            found = self.find(root=root, name="", kind="files", limit=limit + 1)
        except Exception as exc:
            # A missing root makes `find` raise "not found" (it does not return
            # an empty result). Family names vary per trial, so the likeliest
            # cause is a stale family name — surface the live family list.
            if family.startswith("/"):
                raise
            fams = self._proc_families()
            fam_key = family.strip("/")
            if scope and fam_key in fams:
                raise RuntimeError(
                    f"ws.proc: nothing under {root!r}. Family {fam_key!r} "
                    f"exists but scope {scope!r} did not resolve — check the "
                    "partition value (a customer id / brand / city / store id)."
                ) from exc
            raise RuntimeError(
                f"ws.proc: /proc family {fam_key!r} not found. /proc families "
                f"in this trial: {fams}. Family names can differ per trial — "
                "pass one of these."
            ) from exc
        paths = sorted(p for p in found.get("paths", []) if p.endswith(".json"))
        truncated = bool(found.get("truncated")) or len(paths) > limit
        records = [self.read_json(p) for p in paths[:limit]]
        return {"records": records, "count": len(records), "truncated": truncated}

    def _proc_families(self) -> list[str]:
        """Live `/proc` family dir names (they can differ per trial)."""
        try:
            return [
                e["name"]
                for e in self.list("/proc").get("entries", [])
                if e.get("kind") == "NODE_KIND_DIR"
            ]
        except Exception:
            return []

    # ── filesystem mutations ──────────────────────────────────────────────
    def write(self, path: str, content: str, if_match_sha256: str = "") -> dict:
        self._audit("write", {"path": path, "bytes": len(content)})
        return _to_dict(
            self._vm.write(
                WriteRequest(path=path, content=content, if_match_sha256=if_match_sha256)
            )
        )

    def delete(self, path: str) -> dict:
        self._audit("delete", {"path": path})
        return _to_dict(self._vm.delete(DeleteRequest(path=path)))

    # ── /bin/* runtime tools ──────────────────────────────────────────────
    def exec_tool(
        self,
        path: str,
        args: Iterable[str] | None = None,
        stdin: str = "",
    ) -> dict:
        """argv-style invoke of a runtime tool, e.g. `/bin/checkout`."""
        argv = list(args) if args else []
        self._audit("exec", {"path": path, "args": argv, "stdin_bytes": len(stdin)})
        return _to_dict(
            self._vm.exec(ExecRequest(path=path, args=argv, stdin=stdin))
        )

    def jq(
        self,
        filter: str,
        path: str = "",
        *,
        stdin: str = "",
        raw: bool = False,
    ) -> dict:
        """Thin wrapper over `/bin/jq` (added to the runtime when `/bin/sql`
        went down).

        **Minimal jq only** — the runtime build supports just `.`, `keys`,
        `length`, `.field`, `.nested.field`, `.array[0]`, `.array[]`. No
        pipes, no `select()`, no `map()`, no arithmetic. For anything richer
        read the record with `ws.read_json` and filter in Python (strictly
        more powerful). Use this for spot-checks: a record's `keys`, one
        field, a quick `.array[]` walk.

        Returns the exec dict `{stdout, exit_code, stderr}`; jq prints one
        JSON value per output line (text), so the caller decides how to parse
        `stdout`. The runtime's `/bin/jq` prepends a `PowerTools E-Commerce
        OS jq` banner line to stdout on every call — this strips it so
        `stdout` is the bare jq result. Raises on non-zero exit.
        """
        args = (["-r"] if raw else []) + [filter]
        if path:
            args.append(path)
        res = self.exec_tool("/bin/jq", args=args, stdin=stdin)
        if res["exit_code"] != 0:
            raise RuntimeError(
                res["stderr"] or f"ws.jq: /bin/jq failed (exit {res['exit_code']})"
            )
        banner = "PowerTools E-Commerce OS jq\n"
        if res.get("stdout", "").startswith(banner):
            res["stdout"] = res["stdout"][len(banner):]
        return res

    def sql(self, query: str, json_output: bool = True) -> dict:
        args = ["--json"] if json_output else []
        return self.exec_tool("/bin/sql", args=args, stdin=query)

    # Matches the truncation footer /bin/sql appends when a SELECT exceeds
    # the per-call row cap, e.g. "warning: result truncated at 100 rows".
    # Loose enough to survive minor wording changes (truncated/limited,
    # singular/plural rows, different cap number).
    _TRUNC_RE = re.compile(
        r"warning\b[^\n]*\b(?:truncated|limited)\b[^\n]*?\b(\d+)\s+rows?\b",
        re.IGNORECASE,
    )

    def _sql_page(self, query: str) -> tuple[list[dict], int | None]:
        """Run one `/bin/sql --json` call. Returns (rows, page_cap).

        ``page_cap`` is the integer parsed out of the truncation footer
        when it is present (signalling the harness capped this call at
        N rows), otherwise ``None``.
        """
        res = self.sql(query)
        if res["exit_code"] != 0:
            stderr = res["stderr"] or ""
            if "cluster is down" in stderr or "Login timeout" in stderr:
                first = stderr.splitlines()[0] if stderr else "login timeout"
                raise RuntimeError(
                    "ws.sql: the PowerTools SQL cluster is unreachable. The "
                    "warehouse is also exposed as a file-shaped projection — "
                    "read it from /proc instead: ws.proc(<family>) for a whole "
                    "family, ws.read_json(<path>) for one record, ws.jq(...) "
                    "for a quick field pull. List /proc to see this trial's "
                    "families (names can differ per trial). Family map: "
                    f"bin-help/sqlite_schema.txt. Retry SQL only once the "
                    f"cluster has recovered. Original error: {first}"
                )
            raise RuntimeError(
                stderr
                or f"ws.sql_rows: /bin/sql failed (exit {res['exit_code']})"
            )
        stdout = res["stdout"]
        m = self._TRUNC_RE.search(stdout)
        if m:
            page_cap: int | None = int(m.group(1))
            json_part = stdout[: m.start()].rstrip()
        else:
            page_cap = None
            json_part = stdout.strip()
        if not json_part:
            return [], page_cap
        try:
            parsed = json.loads(json_part)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"ws.sql_rows: cannot parse /bin/sql json output: {exc}; "
                f"head={json_part[:200]!r}"
            ) from exc
        if not isinstance(parsed, list):
            parsed = [parsed]
        return parsed, page_cap

    def sql_rows(self, query: str, limit: int = 1000) -> dict:
        """Run a SELECT and harvest up to ``limit`` rows.

        Returns ``{"rows": list[dict], "row_count": int, "truncated": bool}``.
        ``truncated=True`` ⇔ we capped the result at ``limit`` and at least
        one more row was available. To page further re-issue the query
        with an explicit ``LIMIT/OFFSET`` clause (then use
        ``row_count < limit`` as the end-of-data signal).

        The query goes out to ``/bin/sql`` unchanged unless the harness
        truncates the result — in that case the helper wraps the query as
        a subquery and pages through ``LIMIT/OFFSET`` until ``limit``
        rows are gathered or the result is exhausted. The harness row
        cap is invisible to the caller.

        For stable pagination on large tables include an
        ``ORDER BY <stable_key>`` in the query.
        """
        if limit < 1:
            raise ValueError(f"ws.sql_rows: limit must be >= 1 (got {limit})")
        stripped = query.strip().rstrip(";").strip()
        if not stripped:
            raise ValueError("ws.sql_rows: empty query")

        # First call sends the user query verbatim. The 95% case fits
        # under the harness cap and we never touch the SQL.
        rows, page_cap = self._sql_page(stripped)

        if page_cap is not None:
            # Harness truncated. Page the rest with a subquery wrap.
            target = limit + 1
            while len(rows) < target:
                ask = min(target - len(rows), page_cap)
                wrapped = (
                    f"SELECT * FROM ({stripped}) LIMIT {ask} OFFSET {len(rows)}"
                )
                page, cap = self._sql_page(wrapped)
                rows.extend(page)
                if cap is not None and cap < page_cap:
                    page_cap = cap
                # End conditions: short page without marker means data
                # is exhausted; an empty page is a defensive bail.
                if cap is None and len(page) < ask:
                    break
                if not page:
                    break

        truncated = len(rows) > limit
        if truncated:
            rows = rows[:limit]
        return {
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
        }

    def date(self) -> str:
        """Current simulation time from `/bin/date`, as the ISO-8601 string
        it prints (e.g. ``2026-05-25T09:13:19Z``).

        Returns the bare timestamp string — not the raw ``{stdout, ...}``
        exec wrapper — so you can use it directly (compare, or
        ``datetime.fromisoformat(ws.date().replace("Z", "+00:00"))``).
        Raises on tool failure: the sim-date is always available inside a
        trial, so a non-zero exit is a real error, not a branch to handle.
        """
        res = self.exec_tool("/bin/date")
        if res["exit_code"] != 0:
            raise RuntimeError(
                res["stderr"] or f"ws.date: /bin/date failed (exit {res['exit_code']})"
            )
        return res["stdout"].strip()

    def id(self) -> dict:
        """Agent identity from `/bin/id`, parsed into a flat dict.

        `/bin/id` prints one ``key: value`` per line (e.g. ``user: cust_038``
        / ``roles: customer``); every line is parsed so ``ws.id()["user"]``
        and ``ws.id()["roles"]`` work directly — this returns the parsed
        fields, not the raw ``{stdout, exit_code, stderr}`` exec wrapper.
        Values are kept verbatim as printed (``roles`` stays a string; split
        it yourself if a trial ever lists several). Raises on tool failure:
        identity is always available inside a trial.
        """
        res = self.exec_tool("/bin/id")
        if res["exit_code"] != 0:
            raise RuntimeError(
                res["stderr"] or f"ws.id: /bin/id failed (exit {res['exit_code']})"
            )
        fields: dict[str, str] = {}
        for line in res["stdout"].splitlines():
            key, sep, value = line.partition(":")
            if not sep:
                continue
            fields[key.strip()] = value.strip()
        return fields

    # ── terminal answer ───────────────────────────────────────────────────
    def answer(self, scratchpad: dict, verify) -> None:
        if not callable(verify):
            raise ValueError(
                "ws.answer: verify must be a callable that returns True/False."
            )
        try:
            ok = verify(scratchpad)
        except Exception as exc:
            raise ValueError(f"ws.answer: verify raised: {exc}") from exc
        if not ok:
            raise ValueError(
                "ws.answer: verify(scratchpad) returned False — fix scratchpad."
            )

        outcome = scratchpad.get("outcome", "OUTCOME_OK")
        if outcome not in _OUTCOME_MAP:
            raise ValueError(
                f"ws.answer: unknown outcome {outcome!r}; valid: {list(_OUTCOME_MAP)}"
            )
        message = scratchpad.get("answer", scratchpad.get("message", ""))
        refs_raw = scratchpad.get("refs") or []
        refs = [r for r in refs_raw if isinstance(r, str)]

        self._audit(
            "answer",
            {"outcome": outcome, "message_bytes": len(message), "refs": refs},
        )
        self._vm.answer(
            AnswerRequest(message=message, outcome=_OUTCOME_MAP[outcome], refs=refs)
        )

        payload = {"message": message, "outcome": outcome, "refs": refs}
        with contextlib.suppress(OSError):
            Path(self._answer_path).write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
