from pathlib import Path
import re


ARCHIVE = Path(__file__).resolve().parents[2]
REPO = ARCHIVE.parents[3]


def test_archive_metadata_and_pr_evidence():
    version_manifest = (ARCHIVE / "manifest.yaml").read_text(encoding="utf-8")
    package_notes = (ARCHIVE / "notes.md").read_text(encoding="utf-8")
    pr_description = (ARCHIVE / "PR_DESCRIPTION.md").read_text(encoding="utf-8")
    device_readme = (ARCHIVE / "test_package" / "README-harmonyos-device.md").read_text(
        encoding="utf-8"
    )
    drafts = [
        REPO / "knowledge" / "drafts" / "E429-draft-D7A3.kv",
        REPO / "knowledge" / "drafts" / "E429-draft-D7A3.md",
    ]
    assert all(path.is_file() for path in drafts), "the route-C graph draft must be present"
    draft_text = "\n".join(path.read_text(encoding="utf-8") for path in drafts)

    assert 'version: "0.15"' in version_manifest
    assert "https://github.com/jjsullivan5196/wvkbd" in version_manifest
    assert "knowledge_gained:" in version_manifest
    assert "Wayland" in package_notes
    assert "C01" in package_notes and "D01" in package_notes
    assert "路径 C" in pr_description and "路径 B" in pr_description
    assert "上游用例通过率" in pr_description
    assert "鸿蒙特有测试" in pr_description
    assert "did not emit `inputStop`" in device_readme
    assert "transition_focus" in device_readme
    assert "pending the user-supplied signed pair" not in device_readme
    assert "root_cause:" in draft_text and "error_signature:" in draft_text

    public_evidence = "\n".join(
        [version_manifest, package_notes, pr_description, device_readme, draft_text]
    )
    assert not re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}\b", public_evidence)
    assert not re.search(
        r"(?:storePassword|keyPassword|privateKey)\s*[:=]\s*[\"'][^\"']+[\"']",
        public_evidence,
        flags=re.IGNORECASE,
    )
