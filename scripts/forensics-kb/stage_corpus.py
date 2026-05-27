"""Stage the forensics knowledge base for Vertex AI Search ingestion.

Reads source content from this repo and writes:
  out/docs/<id>.txt   — plain-text body for each document
  out/metadata.jsonl  — one JSON line per doc, the format Vertex AI Search
                        expects when importing from GCS with structured metadata

Run from repo root:
    python scripts/forensics-kb/stage_corpus.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "scripts" / "forensics-kb" / "out"
DOCS_DIR = OUT_DIR / "docs"
MARKETING_BASE = "https://www.ai-identity.co"
GITHUB_BASE = "https://github.com/Levaj2000/AI-Identity/blob/main"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return s.strip("-")[:80]


def write_doc(doc_id: str, title: str, body: str, source_url: str, tags: list[str]) -> dict:
    path = DOCS_DIR / f"{doc_id}.txt"
    path.write_text(body, encoding="utf-8")
    return {
        "id": doc_id,
        "structData": {
            "title": title,
            "source_url": source_url,
            "tags": tags,
        },
        "content": {
            "mimeType": "text/plain",
            "uri": f"gs://__BUCKET__/docs/{doc_id}.txt",
        },
    }


def extract_blog_posts() -> list[dict]:
    """Load blog posts from the JSON dump produced by dump_blog_posts.mjs.

    Run before this script:
        (cd landing-page && npx --yes tsx ../scripts/forensics-kb/dump_blog_posts.mjs) \
            > scripts/forensics-kb/out/blog-posts.json
    """
    dump_path = OUT_DIR / "blog-posts.json"
    if not dump_path.exists():
        raise SystemExit(
            "Missing out/blog-posts.json. Run the tsx dump first:\n"
            "  (cd landing-page && npx --yes tsx ../scripts/forensics-kb/dump_blog_posts.mjs) \\\n"
            "    > scripts/forensics-kb/out/blog-posts.json"
        )
    return json.loads(dump_path.read_text())


def stage_blog_posts() -> list[dict]:
    records = []
    for post in extract_blog_posts():
        body_lines = [f"# {post['title']}", "", post.get("excerpt", ""), ""]
        for section in post.get("sections", []):
            body_lines.append(f"## {section['heading']}")
            body_lines.append("")
            for para in section.get("content", []):
                body_lines.append(para)
                body_lines.append("")
        body = "\n".join(body_lines).strip() + "\n"
        records.append(
            write_doc(
                doc_id=f"blog-{post['slug']}",
                title=post["title"],
                body=body,
                source_url=f"{MARKETING_BASE}/blog/{post['slug']}",
                tags=post.get("tags", []),
            )
        )
    return records


def stage_markdown(rel_path: str, doc_id: str, source_url: str, tags: list[str]) -> dict:
    p = REPO_ROOT / rel_path
    text = p.read_text(encoding="utf-8")
    first_h1 = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = first_h1.group(1).strip() if first_h1 else p.stem.replace("-", " ").title()
    return write_doc(doc_id=doc_id, title=title, body=text, source_url=source_url, tags=tags)


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    records.extend(stage_blog_posts())

    records.append(
        stage_markdown(
            "marketing/blog/deepseek-exhibit-a/DeepSeek_Exhibit_A.md",
            doc_id="blog-deepseek-exhibit-a",
            source_url=f"{MARKETING_BASE}/blog/deepseek-as-exhibit-a",
            tags=["DeepSeek", "AI Risk", "Forensics", "Trust"],
        )
    )

    records.append(
        stage_markdown(
            "cli/README.md",
            doc_id="cli-readme",
            source_url=f"{GITHUB_BASE}/cli/README.md",
            tags=["CLI", "Verification", "Audit"],
        )
    )

    for name in ("trust-model", "attestation-format", "key-rotation"):
        records.append(
            stage_markdown(
                f"docs/forensics/{name}.md",
                doc_id=f"forensics-{name}",
                source_url=f"{GITHUB_BASE}/docs/forensics/{name}.md",
                tags=["Forensics", "Internal Docs", name.replace("-", " ").title()],
            )
        )

    meta_path = OUT_DIR / "metadata.jsonl"
    with meta_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"Staged {len(records)} documents into {DOCS_DIR}")
    print(f"Wrote metadata to {meta_path}")
    print("\nNext: replace __BUCKET__ in metadata.jsonl with the GCS bucket name, then upload.")


if __name__ == "__main__":
    main()
