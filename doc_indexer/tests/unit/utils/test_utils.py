import io
import json
import os
import tarfile
from unittest.mock import patch

import pytest

from utils.utils import _parse_github_repo, download_repo, repo_is_archived

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "given_url, expected",
    [
        ("https://github.com/kyma-project/eventing-manager.git", ("kyma-project", "eventing-manager")),
        ("https://github.com/kyma-project/eventing-manager", ("kyma-project", "eventing-manager")),
        ("https://github.com/SAP-docs/btp-cloud-platform.git", ("SAP-docs", "btp-cloud-platform")),
    ],
)
def test_parse_github_repo_valid(given_url, expected):
    assert _parse_github_repo(given_url) == expected


@pytest.mark.parametrize(
    "given_url",
    [
        "https://gitlab.com/kyma-project/eventing-manager.git",  # wrong host
        "git@github.com:kyma-project/eventing-manager.git",  # ssh scheme
        "https://github.com/only-owner",  # missing repo
        "ftp://github.com/a/b",  # bad scheme
        "https://github.com/owner/repo/tree/main",  # extra path segments
        "https://github.com/owner/../evil",  # path traversal attempt
        "https://github.com/../evil-repo",  # path traversal in owner position
    ],
)
def test_parse_github_repo_rejected(given_url):
    with pytest.raises(ValueError):
        _parse_github_repo(given_url)


def _make_repo_tarball(top_dir: str, files: dict[str, str], commit: str | None = None) -> bytes:
    """Build an in-memory .tar.gz that extracts to a single top-level dir, like codeload.

    When *commit* is given it is stored in the pax global "comment" header,
    which is where GitHub archives record the resolved commit SHA.
    """
    buf = io.BytesIO()
    pax_headers = {"comment": commit} if commit else {}
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT, pax_headers=pax_headers) as tf:
        for rel_path, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=f"{top_dir}/{rel_path}")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class _FakeResponse(io.BytesIO):
    """Minimal context-manager wrapper mimicking urlopen's response object."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def test_download_repo_extracts_and_strips_wrapper(tmp_path):
    # Given: a codeload-style tarball whose top dir is "<repo>-<sha>"
    repo_url = "https://github.com/kyma-project/eventing-manager.git"
    tar_bytes = _make_repo_tarball(
        "eventing-manager-HEAD",
        {"README.md": "# hello", "docs/user/guide.md": "guide"},
        commit="abc123",
    )
    dest = str(tmp_path)

    # When
    with patch("utils.utils.urllib.request.urlopen", return_value=_FakeResponse(tar_bytes)):
        downloaded = download_repo(repo_url, dest)
    repo_path = downloaded.path

    # Then: files live directly under <dest>/<repo>, wrapper dir stripped
    assert repo_path == os.path.join(dest, "eventing-manager")
    # the commit comes from the pax header, not from the "-HEAD" wrapper suffix
    assert downloaded.commit == "abc123"
    assert downloaded.slug == "kyma-project/eventing-manager"
    assert downloaded.blob_base_url == "https://github.com/kyma-project/eventing-manager/blob/abc123"
    assert os.path.isfile(os.path.join(repo_path, "README.md"))
    assert os.path.isfile(os.path.join(repo_path, "docs", "user", "guide.md"))
    # staging temp dir is cleaned up
    assert set(os.listdir(dest)) == {"eventing-manager"}


def test_download_repo_falls_back_to_wrapper_suffix_for_commit(tmp_path):
    repo_url = "https://github.com/kyma-project/eventing-manager.git"
    tar_bytes = _make_repo_tarball("eventing-manager-def456", {"README.md": "# hello"})

    with patch("utils.utils.urllib.request.urlopen", return_value=_FakeResponse(tar_bytes)):
        downloaded = download_repo(repo_url, str(tmp_path))

    assert downloaded.commit == "def456"


def test_download_repo_replaces_existing_dir(tmp_path):
    repo_url = "https://github.com/kyma-project/eventing-manager.git"
    dest = str(tmp_path)
    stale = os.path.join(dest, "eventing-manager")
    os.makedirs(stale)
    with open(os.path.join(stale, "old.md"), "w") as fh:
        fh.write("stale")

    tar_bytes = _make_repo_tarball("eventing-manager-def456", {"new.md": "fresh"})

    with patch("utils.utils.urllib.request.urlopen", return_value=_FakeResponse(tar_bytes)):
        repo_path = download_repo(repo_url, dest).path

    assert os.path.isfile(os.path.join(repo_path, "new.md"))
    assert not os.path.exists(os.path.join(repo_path, "old.md"))


def test_download_repo_creates_dest_dir(tmp_path):
    repo_url = "https://github.com/kyma-project/eventing-manager.git"
    dest = str(tmp_path / "nonexistent" / "nested")

    tar_bytes = _make_repo_tarball("eventing-manager-abc123", {"README.md": "# hello"})

    with patch("utils.utils.urllib.request.urlopen", return_value=_FakeResponse(tar_bytes)):
        repo_path = download_repo(repo_url, dest).path

    assert os.path.isfile(os.path.join(repo_path, "README.md"))


@pytest.mark.parametrize("archived", [True, False])
def test_repo_is_archived_reads_api_flag(archived):
    payload = json.dumps({"archived": archived}).encode()
    with patch("utils.utils.urllib.request.urlopen", return_value=_FakeResponse(payload)):
        assert repo_is_archived("https://github.com/kyma-project/warden.git") is archived


def test_repo_is_archived_returns_none_when_api_unreachable():
    import urllib.error

    with patch("utils.utils.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
        assert repo_is_archived("https://github.com/kyma-project/warden.git") is None
