"""EDINET API v2: securities reports as Markdown tables built from the XBRL-to-CSV data.

Targets:
  ``edinet:S100XXXX``  a document (書類管理番号) directly.
  ``edinet:7203`` / ``edinet:72030`` / ``edinet:E02144``  the latest 有価証券報告書・
  四半期報告書・半期報告書 of a company, found by walking the daily document lists back
  ``edinet_days`` days (the API has no per-company search).

Requires ``EDINET_API_KEY`` (issued after signing in to the EDINET viewer site; see section 2-3
of the EDINET API v2 spec, ESE140206.pdf). The key is sent as the
``Subscription-Key`` query parameter, as the spec requires; ``core.http`` redacts it from logs.

Values are written exactly as they appear in the CSV (no unit conversion), so every figure
in the output can be traced to the filing.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import re
import tempfile
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from convmd.core.http import download_binary, get_json
from convmd.core.utils import generate_frontmatter, sanitize_filename, unique_output_path

logger = logging.getLogger(__name__)

API_BASE = "https://api.edinet-fsa.go.jp/api/v2"

# docTypeCode values from the EDINET API v2 spec. Corrections (130/150/170) are only
# fetched by docID, not picked as "latest", since they may restate only part of a report.
_LATEST_DOC_TYPES = ("120", "140", "160")  # 有価証券報告書, 四半期報告書, 半期報告書

_DOC_ID_RE = re.compile(r"^S[0-9A-Z]{7}$")
_EDINET_CODE_RE = re.compile(r"^E\d{5}$")
_SEC_CODE_RE = re.compile(r"^[0-9][0-9A-Z]{3}0?$")

# XBRL-to-CSV column names.
COL_ELEMENT = "要素ID"
COL_LABEL = "項目名"
COL_CONTEXT = "コンテキストID"
COL_YEAR = "相対年度"
COL_SCOPE = "連結・個別"
COL_PERIOD = "期間・時点"
COL_UNIT = "単位"
COL_VALUE = "値"
_REQUIRED_COLS = (COL_ELEMENT, COL_LABEL, COL_CONTEXT, COL_YEAR, COL_SCOPE, COL_VALUE)

# Keep whole-company contexts only: plain contexts and the non-consolidated variant.
# Segment/component members (e.g. ``..._FoodsReportableSegmentMember``) would multiply rows.
_PLAIN_CONTEXT_RE = re.compile(r"^[A-Za-z0-9]+(_NonConsolidatedMember)?$")
_EMPTY_VALUES = {"", "－", "-", "―"}

_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("主要な経営指標等", ("SummaryOfBusinessResults",)),
    ("財務諸表", ("jppfs_cor:", "jpigp_cor:")),  # J-GAAP / IFRS
)
_OTHER_SECTION = "その他の数値項目"

_DEI = {
    "filer": "jpdei_cor:FilerNameInJapaneseDEI",
    "edinet_code": "jpdei_cor:EDINETCodeDEI",
    "sec_code": "jpdei_cor:SecurityCodeDEI",
    "doc_type": "jpdei_cor:DocumentTypeDEI",
    "period_end": "jpdei_cor:CurrentPeriodEndDateDEI",
    "fiscal_year_end": "jpdei_cor:CurrentFiscalYearEndDateDEI",
}
_COVER_TITLE = "jpcrp_cor:DocumentTitleCoverPage"  # 有価証券報告書 / 半期報告書 ...
_NUMERIC_RE = re.compile(r"-?\d+(\.\d+)?")


class EdinetError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("EDINET_API_KEY")
    if not key:
        raise EdinetError("EDINET_API_KEY is not set (see README: EDINET API key).")
    return key


def _api_error(payload: Any) -> str | None:
    """Return an error description if ``payload`` is an EDINET error response."""
    if not isinstance(payload, dict):
        return "unexpected response"
    if "StatusCode" in payload:  # 401/429 come back in this shape
        return f"{payload['StatusCode']} {payload.get('message', '')}".strip()
    meta = payload.get("metadata") or {}
    status = str(meta.get("status", "200"))
    if status != "200":
        return f"{status} {meta.get('message', '')}".strip()
    return None


def list_documents(day: date, key: str) -> list[dict[str, Any]]:
    """Return the documents submitted on ``day`` (書類一覧API, type=2)."""
    url = f"{API_BASE}/documents.json?date={day.isoformat()}&type=2&Subscription-Key={key}"
    payload = get_json(url)
    if payload is None:
        raise EdinetError(f"documents.json request failed for {day}")
    err = _api_error(payload)
    if err:
        raise EdinetError(f"documents.json {day}: {err}")
    return list(payload.get("results") or [])


def _matches_company(doc: dict[str, Any], code: str) -> bool:
    if _EDINET_CODE_RE.match(code):
        return doc.get("edinetCode") == code
    sec = code if len(code) == 5 else code + "0"
    return doc.get("secCode") == sec


def find_latest_report(
    code: str, key: str, days: int, *, today: date | None = None
) -> dict[str, Any] | None:
    """Walk the daily lists back from ``today`` and return the newest matching report."""
    start = today or date.today()
    for i in range(days):
        day = start - timedelta(days=i)
        if day.weekday() >= 5:  # nothing is filed on weekends
            continue
        if i and i % 30 == 0:
            logger.info(f"EDINET: searched back to {day} for {code}...")
        hits = [
            d
            for d in list_documents(day, key)
            if _matches_company(d, code)
            and d.get("docTypeCode") in _LATEST_DOC_TYPES
            and d.get("csvFlag") == "1"
            and d.get("withdrawalStatus") == "0"
        ]
        if hits:
            return max(hits, key=lambda d: str(d.get("submitDateTime") or ""))
    return None


def _decode_csv(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    if b"\x00" in data[:200]:
        return data.decode("utf-16-le")
    return data.decode("utf-8-sig")


def read_csv_rows(zip_path: Path) -> list[dict[str, str]]:
    """Read the report's XBRL_TO_CSV files (audit reports ``jpaud*`` excluded)."""
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(zip_path) as zf:
        names = [
            n
            for n in zf.namelist()
            if n.lower().endswith(".csv") and not Path(n).name.startswith("jpaud")
        ]
        for name in names:
            reader = csv.DictReader(io.StringIO(_decode_csv(zf.read(name))), delimiter="\t")
            missing = [c for c in _REQUIRED_COLS if c not in (reader.fieldnames or [])]
            if missing:
                raise EdinetError(f"{name}: unexpected CSV header {reader.fieldnames}")
            rows.extend(reader)
    if not rows:
        raise EdinetError("no XBRL_TO_CSV data in the downloaded archive")
    return rows


def _format_value(value: str) -> str:
    if re.fullmatch(r"-?\d{4,}", value):
        return f"{int(value):,}"
    return value.replace("|", "\\|").replace("\n", " ")


def _section_of(element: str) -> str:
    for name, needles in _SECTIONS:
        if any(n in element for n in needles):
            return name
    return _OTHER_SECTION


def _year_rank(year: str) -> int:
    """Current period first, then prior, then two periods back (当中間期 → 前中間期 → 前々期末)."""
    if year.startswith("当"):
        return 0
    if year.startswith("前々"):
        return 2
    if year.startswith("前"):
        return 1
    return 9


def render_markdown(rows: list[dict[str, str]]) -> tuple[dict[str, str], str]:
    """Return (DEI metadata, Markdown body) for the CSV rows.

    Tables are split by section, by 連結・個別 (heading shown only when a section has more
    than one), and by 期間/時点 so that flow items (PL/CF) and balances (BS) don't share
    mostly-empty columns.
    """
    by_element = {r[COL_ELEMENT]: r[COL_VALUE] for r in rows if r[COL_ELEMENT].startswith("jpdei")}
    dei = {k: by_element.get(element, "") for k, element in _DEI.items()}
    dei["title"] = next((r[COL_VALUE] for r in rows if r[COL_ELEMENT] == _COVER_TITLE), "")

    # (section, scope, period) -> row key -> {year: value}; insertion order follows the filing.
    tables: dict[tuple[str, str, str], dict[tuple[str, str], dict[str, str]]] = {}
    labels: dict[tuple[str, str], str] = {}
    years: dict[tuple[str, str, str], list[str]] = {}
    for r in rows:
        element, value = r[COL_ELEMENT], (r[COL_VALUE] or "").strip()
        if (
            element.startswith("jpdei")
            or element.endswith("TextBlock")
            or value in _EMPTY_VALUES
            or not _PLAIN_CONTEXT_RE.match(r[COL_CONTEXT])
        ):
            continue
        section = _section_of(element)
        if section == _OTHER_SECTION and not _NUMERIC_RE.fullmatch(value):
            continue  # cover-page text (address, representative, ...) is not a figure
        tkey = (section, r[COL_SCOPE] or "-", r.get(COL_PERIOD) or "-")
        rkey = (element, r.get(COL_UNIT, ""))
        year = r[COL_YEAR] or "-"
        labels[rkey] = r[COL_LABEL]
        tables.setdefault(tkey, {}).setdefault(rkey, {}).setdefault(year, value)
        year_list = years.setdefault(tkey, [])
        if year not in year_list:
            year_list.append(year)

    out: list[str] = [
        "> [!NOTE] EDINET XBRL（CSV）の値をそのまま転記（単位は「単位」列）。"
        "テキストブロック・セグメント別の値は省略。\n"
    ]
    for section in [name for name, _ in _SECTIONS] + [_OTHER_SECTION]:
        keys = [k for k in tables if k[0] == section]
        if not keys:
            continue
        out.append(f"## {section}\n")
        multi_scope = len({k[1] for k in keys}) > 1
        for tkey in keys:
            _, scope, period = tkey
            cols = sorted(years[tkey], key=lambda y: (_year_rank(y), years[tkey].index(y)))
            out.append(f"### {scope} / {period}\n" if multi_scope else f"### {period}\n")
            out.append("| 項目名 | " + " | ".join(cols) + " | 単位 |")
            out.append("|---|" + "---:|" * len(cols) + "---|")
            for rkey, cells in tables[tkey].items():
                vals = [_format_value(cells.get(c, "")) for c in cols]
                out.append(f"| {labels[rkey]} | " + " | ".join(vals) + f" | {rkey[1]} |")
            out.append("")
    return dei, "\n".join(out)


def _download_csv_zip(doc_id: str, key: str, dest: Path) -> None:
    url = f"{API_BASE}/documents/{doc_id}?type=5&Subscription-Key={key}"
    if not download_binary(url, dest):
        raise EdinetError(f"download failed for {doc_id}")
    if not zipfile.is_zipfile(dest):
        # Errors come back as JSON with HTTP 200 in some cases.
        try:
            import json

            err = _api_error(json.loads(dest.read_text(encoding="utf-8", errors="ignore")))
        except ValueError:
            err = "response is neither ZIP nor JSON"
        raise EdinetError(f"{doc_id}: {err}")


def convert_edinet(target: str, output_dir: Path, edinet_days: int = 400) -> Path | None:
    code = target.split(":", 1)[1].strip().upper() if ":" in target else target.strip().upper()
    try:
        key = _api_key()
        if _DOC_ID_RE.match(code):
            doc_id = code
        elif _EDINET_CODE_RE.match(code) or _SEC_CODE_RE.match(code):
            logger.info(f"EDINET: looking up the latest report for {code} (up to {edinet_days} days)...")
            doc = find_latest_report(code, key, edinet_days)
            if doc is None:
                logger.error(f"EDINET: no report with CSV for {code} in the last {edinet_days} days.")
                return None
            doc_id = str(doc["docID"])
            logger.info(f"EDINET: found {doc_id} {doc.get('docDescription')} ({doc.get('submitDateTime')})")
        else:
            logger.error(f"EDINET: '{code}' is not a docID (S…), EDINET code (E…), or securities code.")
            return None

        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / f"{doc_id}.zip"
            _download_csv_zip(doc_id, key, zip_path)
            rows = read_csv_rows(zip_path)
    except EdinetError as e:
        logger.error(f"EDINET: {e}")
        return None

    dei, body = render_markdown(rows)
    doc_title = dei.pop("title") or dei["doc_type"]
    title = " ".join(x for x in (dei["filer"], doc_title, dei["period_end"]) if x) or doc_id
    source = f"{API_BASE}/documents/{doc_id}?type=5"
    extra = {k: v for k, v in dei.items() if v and k != "filer"}
    extra["doc_id"] = doc_id
    extra["extraction"] = "xbrl"
    frontmatter = generate_frontmatter(title, source, tags=["edinet", "xbrl"], extra=extra)

    output_dir.mkdir(parents=True, exist_ok=True)
    path = unique_output_path(output_dir, sanitize_filename(title), source)
    path.write_text(f"{frontmatter}# {title}\n\n{body}", encoding="utf-8")
    logger.info(f"Saved to {path}")
    return path
