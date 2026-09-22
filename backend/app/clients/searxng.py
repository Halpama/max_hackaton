import httpx

SEARXNG_URL = "http://searxng:8080"  # внутренний порт в docker-сети, не 8081

def search(query: str, top_k: int = 5, snippet_len: int = 200) -> list[dict]:
    resp = httpx.get(
        f"{SEARXNG_URL}/search",
        params={"q": query, "format": "json"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("results", [])[:top_k]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": (item.get("content") or "")[:snippet_len],
        })
    return results