# Obsidian Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `convMD`を強化し、Obsidian向けの厳密なYAMLフロントマター出力、AIによるWikiリンク置換、およびLocal REST API経由での直接インポート機能を追加する。

**Architecture:** 
- `utils.py` の `generate_frontmatter` を改修し、Obsidian互換のYAMLを生成。
- `transform.py` のプロンプトと後処理ロジックを強化し、Wikiリンク置換とタグ抽出を行う。
- `integrations/obsidian.py` を新設（または改修）し、Local REST APIへのPUTリクエスト送信機能（フォールバック付き）を実装し、`pipeline.py` から呼び出す。

**Tech Stack:** Python 3.10+, httpx, Obsidian Local REST API, Gemini API

---

### Task 1: フロントマター生成ロジックの強化

**Files:**
- Modify: `src/convmd/core/utils.py`
- Test: `tests/test_utils.py`

- [ ] **Step 1: Write the failing test**

```python
import datetime
from convmd.core.utils import generate_frontmatter

def test_generate_frontmatter_obsidian_style():
    # extra args contain a mix of types to test serialization
    frontmatter = generate_frontmatter(
        title="Test Title",
        source_url="https://example.com",
        tags=["a", "b"],
        author="John",
        extra={"aliases": ["Alt"], "custom_id": 123}
    )
    
    assert "---\n" in frontmatter
    assert 'title: "Test Title"' in frontmatter
    assert 'source: "https://example.com"' in frontmatter
    assert 'author: "John"' in frontmatter
    # Tags should be a YAML list
    assert 'tags:\n  - a\n  - b\n' in frontmatter
    assert 'aliases:\n  - Alt\n' in frontmatter
    assert 'custom_id: 123' in frontmatter
    assert 'created_at: ' in frontmatter # Should exist
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_utils.py -k test_generate_frontmatter_obsidian_style`
Expected: FAIL (Because current generate_frontmatter uses naive string formatting for tags/extra)

- [ ] **Step 3: Write minimal implementation**

```python
# In src/convmd/core/utils.py
import datetime
import json
from typing import Any

def _yaml_format(value: Any, indent: int = 0) -> str:
    """Helper to format values as basic YAML without external libraries."""
    padding = " " * indent
    if isinstance(value, list):
        if not value:
            return "[]"
        items = [f"\n{padding}  - {v}" for v in value]
        return "".join(items)
    elif isinstance(value, str):
        # Escape quotes and wrap in quotes
        safe_val = value.replace('"', '\\"')
        return f'"{safe_val}"'
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)

def generate_frontmatter(
    title: str,
    source_url: str,
    tags: list[str] | None = None,
    author: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Generate YAML frontmatter block for Obsidian compatibility."""
    lines = ["---", f'title: {_yaml_format(title)}', f'source: {_yaml_format(source_url)}']
    
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append(f"created_at: {_yaml_format(now_iso)}")
    
    if author:
        lines.append(f"author: {_yaml_format(author)}")
        
    if tags:
        lines.append(f"tags:{_yaml_format(tags)}")
        
    if extra:
        for k, v in extra.items():
            if k == "aliases" and isinstance(v, list):
                lines.append(f"aliases:{_yaml_format(v)}")
            else:
                lines.append(f"{k}: {_yaml_format(v)}")
                
    lines.append("---\n\n")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_utils.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/convmd/core/utils.py tests/test_utils.py
git commit -m "feat: enhance YAML frontmatter generation for Obsidian compatibility"
```

---

### Task 2: 自動Wikiリンクとタグ付けの強化（AIプロンプトと後処理）

**Files:**
- Modify: `src/convmd/core/transform.py`
- Test: `tests/test_transform.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from unittest.mock import patch
from convmd.core.transform import apply_obsidian_links

@patch("convmd.core.transform.gemini.is_configured", return_value=True)
@patch("convmd.core.transform.gemini.generate_text")
def test_apply_obsidian_links(mock_generate, mock_config, tmp_path):
    # Setup test file
    test_file = tmp_path / "test.md"
    test_file.write_text("---\ntitle: \"Test\"\ntags:\n  - raw\n---\n\n徳島県は阿波国と呼ばれていた。", encoding="utf-8")
    
    # Mock AI response with tags at the end
    mock_generate.return_value = "[[徳島県]]は[[阿波国]]と呼ばれていた。\n\nTAGS: 徳島, 歴史"
    
    out_path = apply_obsidian_links(test_file)
    
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    
    # Check if tags were injected into frontmatter
    assert "tags:\n  - raw\n  - 徳島\n  - 歴史" in content
    # Check if text was linked
    assert "[[徳島県]]は[[阿波国]]" in content
    # Check if TAGS marker was removed from body
    assert "TAGS:" not in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_transform.py -k test_apply_obsidian_links`
Expected: FAIL (because current implementation doesn't parse or inject tags back into frontmatter)

- [ ] **Step 3: Write minimal implementation**

```python
# In src/convmd/core/transform.py

import re

_AUTO_LINK_INSTRUCTION = (
    "このMarkdown文章から重要な固有名詞、専門用語、または概念を抽出し、"
    "それらをObsidianの内部リンクフォーマットである `[[キーワード]]` に置き換えてください。"
    "また、文章全体を要約するような適切なタグ（例: `歴史`, `AI`）を3〜5個生成し、"
    "出力するファイルの最後の一行に `TAGS: タグ1, タグ2` の形式で出力してください。\n"
    "【厳守】\n"
    "元の文章の意味、改行、見出し、画像リンク、フロントマターなどは絶対に壊さないでください。"
)

def apply_obsidian_links(file_path: Path) -> Path | None:
    """Auto-link important keywords as [[wikilinks]] and inject tags."""
    if not gemini.is_configured():
        return None

    logger.info(f"Applying Obsidian Auto-Links to {file_path.name}...")
    original_content = file_path.read_text(encoding="utf-8")
    prompt = _TRANSFORM_TEMPLATE.format(
        instruction=_AUTO_LINK_INSTRUCTION,
        text=original_content,
    )
    out_path = file_path.parent / f"{file_path.stem}{Suffix.LINKED}"
    
    text = gemini.generate_text(prompt)
    if text is None:
        return None
        
    # Extract tags from the end
    tags = []
    lines = text.strip().split('\n')
    if lines and lines[-1].startswith('TAGS:'):
        tag_line = lines.pop()
        raw_tags = tag_line.replace('TAGS:', '').split(',')
        tags = [t.strip() for t in raw_tags if t.strip()]
        text = '\n'.join(lines)
        
    # Inject tags into frontmatter
    if tags:
        # Simple injection assuming basic YAML format
        if "tags:\n" in text:
            tag_yaml = "\n".join([f"  - {t}" for t in tags]) + "\n"
            text = text.replace("tags:\n", f"tags:\n{tag_yaml}", 1)
        elif "---\n" in text:
            # Add tags property if missing but frontmatter exists
            tag_yaml = "tags:\n" + "\n".join([f"  - {t}" for t in tags]) + "\n"
            text = text.replace("---\n", f"---\n{tag_yaml}", 1)
            
    out_path.write_text(text + "\n", encoding="utf-8")
    logger.info(f"Auto-Linking completed. Saved to: {out_path}")
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_transform.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/convmd/core/transform.py tests/test_transform.py
git commit -m "feat: enhance auto-link prompt and auto-inject generated tags into frontmatter"
```

---

### Task 3: Obsidian Local REST API 連携機能の実装

**Files:**
- Create: `src/convmd/integrations/obsidian_rest.py`
- Modify: `src/convmd/pipeline.py`
- Test: `tests/test_obsidian_rest.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from convmd.integrations.obsidian_rest import export_to_obsidian_api

@patch("convmd.integrations.obsidian_rest.httpx.put")
def test_export_to_obsidian_api_success(mock_put, tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_put.return_value = mock_response
    
    file_path = tmp_path / "test.md"
    file_path.write_text("content", encoding="utf-8")
    
    success = export_to_obsidian_api(file_path, "https://127.0.0.1:27124", "secret-token", "Inbox")
    
    assert success is True
    mock_put.assert_called_once()
    args, kwargs = mock_put.call_args
    assert "https://127.0.0.1:27124/vault/Inbox/test.md" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["headers"]["Content-Type"] == "text/markdown"
    assert kwargs["content"] == b"content"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_obsidian_rest.py`
Expected: FAIL (File not found)

- [ ] **Step 3: Write minimal implementation**

```python
# In src/convmd/integrations/obsidian_rest.py
import logging
from pathlib import Path
import urllib.parse
import httpx

logger = logging.getLogger(__name__)

def export_to_obsidian_api(file_path: Path, api_url: str, token: str, target_folder: str = "Inbox") -> bool:
    """Export a Markdown file directly to Obsidian via Local REST API."""
    if not file_path.exists():
        return False
        
    try:
        content = file_path.read_bytes()
        encoded_folder = urllib.parse.quote(target_folder.strip('/'))
        encoded_filename = urllib.parse.quote(file_path.name)
        
        url = f"{api_url.rstrip('/')}/vault/{encoded_folder}/{encoded_filename}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "text/markdown"
        }
        
        # Local REST API requires HTTPS and self-signed certs are common
        with httpx.Client(verify=False) as client:
            response = client.put(url, headers=headers, content=content, timeout=10.0)
            response.raise_for_status()
            
        logger.info(f"Successfully exported {file_path.name} to Obsidian Vault via API.")
        return True
    except Exception as e:
        logger.error(f"Failed to export to Obsidian API: {e}")
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_obsidian_rest.py`
Expected: PASS

- [ ] **Step 5: Pipeline Integration**

Update `src/convmd/pipeline.py` to use the new export function if configured.

```python
# In src/convmd/pipeline.py, after importing `export_to_obsidian_api` and `os`
import os
from convmd.integrations.obsidian_rest import export_to_obsidian_api

# ... inside `run_pipeline` function, near the end where files are processed

        obsidian_api_url = os.environ.get("OBSIDIAN_REST_API_URL")
        obsidian_api_key = os.environ.get("OBSIDIAN_REST_API_KEY")

        for md_file in generated_files:
            if cfg.auto_link:
                from convmd.core.transform import apply_obsidian_links
                linked_file = apply_obsidian_links(md_file)
                if linked_file:
                    md_file = linked_file
                    
            if obsidian_api_url and obsidian_api_key:
                logger.info(f"Exporting to Obsidian via API: {md_file.name}")
                export_to_obsidian_api(md_file, obsidian_api_url, obsidian_api_key, target_folder="Clippings")
```

- [ ] **Step 6: Commit**

```bash
git add src/convmd/integrations/obsidian_rest.py src/convmd/pipeline.py tests/test_obsidian_rest.py
git commit -m "feat: add Obsidian Local REST API export integration"
```

---
