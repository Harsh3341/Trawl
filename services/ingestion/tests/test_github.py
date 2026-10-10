import json, pathlib, respx, httpx
from app.github import GitHubReleaseClient

FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/releases.json").read_text())


@respx.mock
def test_fetch_releases_maps_fields():
    respx.get("https://api.github.com/repos/acme/widget/releases").mock(
        return_value=httpx.Response(200, json=FIXTURE))
    rels = GitHubReleaseClient().fetch_releases("acme/widget")
    assert len(rels) == 2
    assert rels[0].url == "https://github.com/acme/widget/releases/tag/v2.0.0"
    assert rels[0].title == "v2.0.0"
    assert rels[0].version == "v2.0.0"
    assert "dark mode" in rels[0].body
    assert rels[1].title == "v1.9.0"   # falls back to tag_name when name is empty
