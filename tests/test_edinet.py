"""EDINET API v2 parser: CSV parsing, rendering, latest-report lookup, routing, key redaction."""

import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from convmd.core.http import redact
from convmd.parsers.media import edinet

HEADER = ["要素ID", "項目名", "コンテキストID", "相対年度", "連結・個別", "期間・時点", "ユニットID", "単位", "値"]
ROWS = [
    ["jpdei_cor:FilerNameInJapaneseDEI", "提出者名", "FilingDateInstant", "提出日時点", "その他", "時点", "", "", "テスト食品株式会社"],
    ["jpdei_cor:DocumentTypeDEI", "様式", "FilingDateInstant", "提出日時点", "その他", "時点", "", "", "第三号様式"],
    ["jpdei_cor:CurrentPeriodEndDateDEI", "期末日", "FilingDateInstant", "提出日時点", "その他", "時点", "", "", "2025-12-31"],
    ["jpcrp_cor:NetSalesSummaryOfBusinessResults", "売上高", "Prior1YearDuration", "前期", "連結", "期間", "JPY", "円", "3000000000"],
    ["jpcrp_cor:NetSalesSummaryOfBusinessResults", "売上高", "CurrentYearDuration", "当期", "連結", "期間", "JPY", "円", "3467675000000"],
    ["jppfs_cor:NetSales", "売上高", "CurrentYearDuration_NonConsolidatedMember", "当期", "個別", "期間", "JPY", "円", "1200000000"],
    ["jppfs_cor:NetSales", "売上高", "CurrentYearDuration_FoodsReportableSegmentMember", "当期", "連結", "期間", "JPY", "円", "999"],
    ["jpcrp_cor:BusinessRisksTextBlock", "事業等のリスク", "FilingDateInstant", "提出日時点", "その他", "時点", "", "", "<p>長文</p>"],
    ["jpcrp_cor:NumberOfEmployees", "従業員数", "CurrentYearInstant", "当期末", "連結", "時点", "pure", "人", "－"],
]


def _make_zip(path: Path, rows=ROWS, header=HEADER) -> Path:
    tsv = "\n".join("\t".join(f'"{c}"' for c in r) for r in [header, *rows])
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("XBRL_TO_CSV/jpcrp030000-asr-001_E99999-000_2025-12-31_01_2026-03-27.csv",
                    tsv.encode("utf-16"))
        zf.writestr("XBRL_TO_CSV/jpaud-aar-cn-001_E99999-000_2025-12-31_01_2026-03-27.csv",
                    "\t".join(HEADER).encode("utf-16"))
    return path


def test_read_and_render(tmp_path):
    rows = edinet.read_csv_rows(_make_zip(tmp_path / "a.zip"))
    dei, body = edinet.render_markdown(rows)
    assert dei["filer"] == "テスト食品株式会社"
    assert "## 主要な経営指標等" in body and "## 財務諸表" in body
    # Columns follow the filing's order; values are verbatim with separators only.
    assert "| 項目名 | 前期 | 当期 | 単位 |" in body
    assert "| 売上高 | 3,000,000,000 | 3,467,675,000,000 | 円 |" in body
    assert "### 個別" in body and "1,200,000,000" in body
    # Segment members, text blocks and empty values are dropped.
    assert "999" not in body and "長文" not in body and "従業員数" not in body


def test_unexpected_header_raises(tmp_path):
    z = _make_zip(tmp_path / "b.zip", header=["a", "b"], rows=[["1", "2"]])
    with pytest.raises(edinet.EdinetError):
        edinet.read_csv_rows(z)


def test_api_error_shapes():
    assert edinet._api_error({"metadata": {"status": "200"}}) is None
    assert edinet._api_error({"metadata": {"status": "404", "message": "Not Found"}}) == "404 Not Found"
    assert edinet._api_error({"StatusCode": 401, "message": "Access denied"}) == "401 Access denied"


def test_find_latest_report_matches_4digit_code_and_skips_weekends():
    calls = []

    def fake_list(day, _key):
        calls.append(day)
        if day == date(2026, 3, 27):
            return [
                {"docID": "S100AAAA", "secCode": "29140", "docTypeCode": "120", "csvFlag": "1",
                 "withdrawalStatus": "0", "submitDateTime": "2026-03-27 09:00"},
                {"docID": "S100BBBB", "secCode": "29140", "docTypeCode": "180", "csvFlag": "0",
                 "withdrawalStatus": "0", "submitDateTime": "2026-03-27 10:00"},
            ]
        return []

    with patch.object(edinet, "list_documents", side_effect=fake_list):
        doc = edinet.find_latest_report("2914", "k", 10, today=date(2026, 3, 30))  # Monday
    assert doc is not None and doc["docID"] == "S100AAAA"
    assert date(2026, 3, 29) not in calls and date(2026, 3, 28) not in calls  # Sun, Sat


def test_convert_by_doc_id_writes_markdown(tmp_path, monkeypatch):
    monkeypatch.setenv("EDINET_API_KEY", "secret")

    def fake_download(url, dest):
        assert "type=5" in url and "S100AAAA" in url
        _make_zip(dest)
        return True

    with patch.object(edinet, "download_binary", side_effect=fake_download):
        path = edinet.convert_edinet("edinet:S100AAAA", tmp_path)
    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert 'source: "https://api.edinet-fsa.go.jp/api/v2/documents/S100AAAA?type=5"' in text
    assert 'extraction: "xbrl"' in text and "secret" not in text


def test_missing_key_returns_none(tmp_path, monkeypatch):
    monkeypatch.delenv("EDINET_API_KEY", raising=False)
    assert edinet.convert_edinet("edinet:S100AAAA", tmp_path) is None


def test_routing_dispatches_edinet_without_llm_fallback(tmp_path):
    from convmd.cli_args import RunConfig
    from convmd.routing import dispatch_url

    cfg = RunConfig(target="edinet:7203", output_dir=tmp_path, ai_extract=True, edinet_days=5)
    with patch("convmd.parsers.media.edinet.convert_edinet", return_value=None) as conv, \
         patch("convmd.core.llm_extractor.extract_with_llm") as llm:
        dispatch_url("edinet:7203", tmp_path, cfg)
    conv.assert_called_once_with("edinet:7203", tmp_path, edinet_days=5)
    llm.assert_not_called()


def test_redact_hides_subscription_key():
    msg = "Client error '401' for url 'https://x/documents.json?date=2026-01-05&Subscription-Key=abc123'"
    assert "abc123" not in redact(msg) and "Subscription-Key=***" in redact(msg)
