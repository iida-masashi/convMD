"""YouTube 字幕 (yt-dlp) → 読める Markdown 変換.

convMD 内蔵の youtube_transcript_api が空応答を返す環境向けの代替経路。
yt-dlp で自動生成字幕(VTT)を取得し、タイムスタンプ・インラインタグ・重複行を
除去して連続した本文に整形、frontmatter 付き Markdown として保存する。

使い方:
    uv run python scripts/yt_subs_to_md.py <動画URL> [<動画URL> ...] \
        --out-dir "./output/youtube"
    uv run python scripts/yt_subs_to_md.py --playlist <playlistURL> \
        --out-dir "./output/youtube"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from convmd.core.utils import sanitize_filename  # 既存のファイル名サニタイズを再利用

_TAG_RE = re.compile(r"<[^>]+>")
_TS_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->")


def _run_ytdlp(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "yt_dlp", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def list_playlist_entries(playlist_url: str) -> list[tuple[str, str]]:
    """playlist から (video_id, title) を列挙."""
    proc = _run_ytdlp(
        ["--flat-playlist", "--print", "%(id)s\t%(title)s", playlist_url]
    )
    if proc.returncode != 0:
        print(f"[WARN] playlist 取得失敗: {proc.stderr[:300]}", file=sys.stderr)
    entries: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if "\t" in line:
            vid, title = line.split("\t", 1)
            entries.append((vid.strip(), title.strip()))
    return entries


_VID_RE = re.compile(r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[?&/]|$)")


def extract_video_id(url: str) -> str | None:
    m = _VID_RE.search(url)
    return m.group(1) if m else None


def fetch_vtt(url: str, tmp: Path) -> Path | None:
    """ja(-orig) 字幕を VTT で取得. 動画本体は DL しない (FFmpeg 不要).

    動画 ID ごとに専用サブディレクトリへ出力し、その ID のファイルだけを返す。
    共有 tmp に全動画の VTT が蓄積して取り違える事故を防ぐ。
    """
    vid = extract_video_id(url)
    if not vid:
        print(f"[WARN] video_id 抽出失敗: {url}", file=sys.stderr)
        return None
    vdir = tmp / vid
    vdir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(vdir / "%(id)s.%(ext)s")
    proc = _run_ytdlp(
        [
            "--write-auto-sub",
            "--sub-lang",
            "ja-orig,ja",
            "--sub-format",
            "vtt",
            "--skip-download",
            "-o",
            out_tmpl,
            url,
        ]
    )
    if proc.returncode != 0:
        print(f"[WARN] 字幕取得失敗 {url}: {proc.stderr[:200]}", file=sys.stderr)
    # この動画 ID のファイルのみを対象に、ja-orig を優先、無ければ ja
    cands = sorted(vdir.glob(f"{vid}*.ja-orig.vtt")) + sorted(vdir.glob(f"{vid}*.ja.vtt"))
    return cands[0] if cands else None


def vtt_to_text(vtt: Path) -> str:
    """VTT を読める連続本文に整形.

    自動字幕は「文の途中→続き→...」が cue ごとに重複する。各 cue の最終確定行
    だけを採用し、直前の行と重複・前方一致するものは捨てて連結する。
    """
    raw = vtt.read_text(encoding="utf-8", errors="replace")
    lines_out: list[str] = []
    for block in raw.split("\n\n"):
        text_lines: list[str] = []
        for ln in block.splitlines():
            if ln.startswith("WEBVTT") or ln.startswith("Kind:") or ln.startswith("Language:"):
                continue
            if _TS_RE.match(ln):
                continue
            cleaned = _TAG_RE.sub("", ln).strip()
            if cleaned:
                text_lines.append(cleaned)
        if not text_lines:
            continue
        # cue の最終行が確定テキスト
        candidate = text_lines[-1]
        if lines_out:
            prev = lines_out[-1]
            # 直前と同一、または直前が candidate の先頭部分（進行中状態）なら置換/スキップ
            if candidate == prev:
                continue
            if candidate.startswith(prev):
                lines_out[-1] = candidate
                continue
            if prev.startswith(candidate):
                continue
        lines_out.append(candidate)
    return "\n".join(lines_out)


def video_title(url_or_id: str) -> str:
    proc = _run_ytdlp(["--skip-download", "--print", "%(title)s", url_or_id])
    t = proc.stdout.strip().splitlines()
    return t[0] if t else url_or_id


def video_meta(url_or_id: str) -> dict[str, str]:
    """タイトル・URL・投稿日・チャンネル・概要欄を取得（字幕不要のメタのみ）."""
    fields = ["title", "webpage_url", "upload_date", "channel", "duration_string", "description"]
    sep = "\x1f"  # 概要欄に改行が含まれるため区切りは制御文字
    proc = _run_ytdlp(
        ["--skip-download", "--print", sep.join(f"%({f})s" for f in fields), url_or_id]
    )
    out = proc.stdout.strip()
    parts = out.split(sep)
    if len(parts) < len(fields):
        parts += [""] * (len(fields) - len(parts))
    return dict(zip(fields, parts, strict=False))


def build_md(title: str, url: str, body: str, channel_tag: str) -> str:
    fm = (
        "---\n"
        f'title: "{title.replace(chr(34), "")}"\n'
        f"source: {url}\n"
        f"tags: [youtube, transcript, 自動字幕, {channel_tag}]\n"
        "evidence_type: auto_caption\n"
        "---\n\n"
    )
    note = (
        "> [!warning] 自動生成字幕\n"
        "> 本文は YouTube の自動生成字幕(yt-dlp 取得)を整形したもの。"
        "音声認識の誤変換を含む。固有名詞・人名・地名は要検証。\n\n"
    )
    return f"{fm}# {title}\n\n{note}{body}\n"


def build_stub_md(meta: dict[str, str], channel_tag: str) -> str:
    """字幕なし動画向け：タイトル/URL/日付など最低限のメタ情報のみの MD."""
    title = meta.get("title", "")
    url = meta.get("webpage_url", "")
    up = meta.get("upload_date", "")
    up_fmt = f"{up[:4]}-{up[4:6]}-{up[6:8]}" if len(up) == 8 else up
    dur = meta.get("duration_string", "")
    desc = meta.get("description", "").strip()
    fm = (
        "---\n"
        f'title: "{title.replace(chr(34), "")}"\n'
        f"source: {url}\n"
        f"upload_date: {up_fmt}\n"
        f"tags: [youtube, {channel_tag}, 字幕なし]\n"
        "evidence_type: metadata_only\n"
        "---\n\n"
    )
    body = (
        f"# {title}\n\n"
        "> [!note] 字幕なし動画\n"
        "> この動画には字幕（自動生成含む）が無いため、本文の文字起こしは未取得。"
        "タイトル・URL・概要欄のみ記録。\n\n"
        "| 項目 | 内容 |\n|---|---|\n"
        f"| URL | {url} |\n"
        f"| 投稿日 | {up_fmt} |\n"
        f"| 長さ | {dur} |\n\n"
    )
    if desc:
        body += "## 概要欄\n\n" + desc + "\n"
    return fm + body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*", help="動画 URL")
    ap.add_argument(
        "--playlist",
        action="append",
        default=[],
        help="playlist URL（複数指定可。動画を列挙して全件変換）",
    )
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--limit", type=int, default=0, help="先頭 N 件に制限(0=無制限)")
    ap.add_argument("--tags", default="まことの道", help="frontmatter に付けるチャンネルタグ")
    ap.add_argument(
        "--meta-fallback",
        action="store_true",
        help="字幕が無い動画はメタ情報のみのスタブ MD を生成",
    )
    ap.add_argument(
        "--meta-only",
        action="store_true",
        help="字幕を取得せず、全件メタ情報スタブ MD のみ生成",
    )
    ap.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="各動画処理の間に挟む秒数（レート制限回避）",
    )
    ap.add_argument(
        "--dedupe",
        action="store_true",
        help="同一 video_id の重複を除去（複数 playlist 指定時）",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets: list[str] = list(args.urls)
    for pl in args.playlist:
        entries = list_playlist_entries(pl)
        print(f"[playlist] {pl} -> {len(entries)} 本")
        for vid, _ in entries:
            targets.append(f"https://youtu.be/{vid}")
    if args.dedupe:
        seen: set[str] = set()
        uniq: list[str] = []
        for u in targets:
            vid = extract_video_id(u) or u
            if vid not in seen:
                seen.add(vid)
                uniq.append(u)
        if len(uniq) != len(targets):
            print(f"[dedupe] {len(targets)} -> {len(uniq)} 本（重複除去）")
        targets = uniq
    if args.limit:
        targets = targets[: args.limit]
    if not targets:
        print("[ERROR] 変換対象がありません。URL か --playlist を指定。", file=sys.stderr)
        return 1

    ok = 0
    stub = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for i, url in enumerate(targets, 1):
            print(f"[{i}/{len(targets)}] {url}")
            vtt = None if args.meta_only else fetch_vtt(url, tmp)
            body = vtt_to_text(vtt) if vtt else ""
            if body.strip():
                title = video_title(url)
                md = build_md(title, url, body, args.tags)
                fname = sanitize_filename(title)[:80] + ".md"
                (out_dir / fname).write_text(md, encoding="utf-8")
                print(f"  -> 本文保存: {fname} ({len(body)} chars)")
                ok += 1
            elif args.meta_only or args.meta_fallback:
                meta = video_meta(url)
                if not meta.get("title"):
                    print("  -> メタ取得失敗、スキップ")
                    continue
                md = build_stub_md(meta, args.tags)
                fname = sanitize_filename(meta["title"])[:80] + ".md"
                (out_dir / fname).write_text(md, encoding="utf-8")
                print(f"  -> メタのみ保存: {fname}")
                stub += 1
            else:
                print("  -> 字幕なし、スキップ")
            if args.sleep and i < len(targets):
                time.sleep(args.sleep)
    print(f"\n完了: 本文 {ok} 本 / メタのみ {stub} 本 / 計 {ok + stub}/{len(targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
