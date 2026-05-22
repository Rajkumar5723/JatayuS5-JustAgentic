from core import profile_enrichment


def test_normalize_eval_profiles_fetches_missing_raw_data(monkeypatch):
    monkeypatch.setattr(
        profile_enrichment,
        "fetch_github_light",
        lambda url: {"username": "rikin0102", "total_repos": 3},
    )
    monkeypatch.setattr(
        profile_enrichment,
        "fetch_leetcode_light",
        lambda url: {"username": "Rajkumar_57", "total": 112, "easy": 85, "medium": 25, "hard": 2},
    )

    payload = profile_enrichment.normalize_eval_profiles(
        {"github_raw": {}, "leetcode_raw": {}},
        github_url="https://github.com/rikin0102/",
        leetcode_url="https://leetcode.com/u/Rajkumar_57/",
    )

    assert payload["github_raw"]["username"] == "rikin0102"
    assert payload["leetcode_raw"]["username"] == "Rajkumar_57"
    assert payload["leetcode_raw"]["total"] == 112
    assert payload["github_url"] == "https://github.com/rikin0102/"
    assert payload["leetcode_url"] == "https://leetcode.com/u/Rajkumar_57/"


def test_normalize_eval_profiles_ignores_empty_marker_urls(monkeypatch):
    calls = {"github": 0, "leetcode": 0}

    def github(_url):
        calls["github"] += 1
        return {"username": "unused"}

    def leetcode(_url):
        calls["leetcode"] += 1
        return {"username": "unused"}

    monkeypatch.setattr(profile_enrichment, "fetch_github_light", github)
    monkeypatch.setattr(profile_enrichment, "fetch_leetcode_light", leetcode)

    payload = profile_enrichment.normalize_eval_profiles({}, github_url="NA", leetcode_url="n/a")

    assert payload["github_raw"] == {}
    assert payload["leetcode_raw"] == {}
    assert calls == {"github": 0, "leetcode": 0}
