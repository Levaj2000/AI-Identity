import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC_SCRIPT = REPO_ROOT / "scripts" / "cosai-docs" / "sync.sh"


def test_sync_refuses_internal_notes_target_before_pandoc(tmp_path: Path) -> None:
    src = tmp_path / "exported.docx"
    dst = tmp_path / "draft.notes.md"
    src.write_bytes(b"placeholder docx")

    result = subprocess.run(
        [str(SYNC_SCRIPT), str(src), str(dst)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "refusing to sync into internal notes target" in result.stderr
    assert not dst.exists()


def test_sync_refuses_non_markdown_target_before_pandoc(tmp_path: Path) -> None:
    src = tmp_path / "exported.docx"
    dst = tmp_path / "snapshot.txt"
    src.write_bytes(b"placeholder docx")

    result = subprocess.run(
        [str(SYNC_SCRIPT), str(src), str(dst)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "target must be a markdown snapshot" in result.stderr
    assert not dst.exists()
