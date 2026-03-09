"""PubMed Search Service - searches PubMed/medical literature."""
import logging
from typing import Any, Dict, List, Optional
import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    pubmed_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    api_key: Optional[str] = None
    request_timeout: int = 30
    class Config:
        env_prefix = "PUBMED_"

settings = Settings()


class PubMedSearchService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        headers = {"User-Agent": "MEDBOT/1.0 (medical-education-bot@example.com)"}
        self._client = httpx.AsyncClient(timeout=settings.request_timeout, headers=headers)
        logger.info("PubMedSearchService started")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Not started")
        return self._client

    async def search(self, query: str, max_results: int = 10, date_range: Optional[str] = None) -> Dict[str, Any]:
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        if settings.api_key:
            params["api_key"] = settings.api_key
        if date_range:
            params["datetype"] = "pdat"
            params["reldate"] = date_range

        try:
            resp = await self.client.get(f"{settings.pubmed_base_url}/esearch.fcgi", params=params)
            resp.raise_for_status()
            data = resp.json()
            ids = data.get("esearchresult", {}).get("idlist", [])
            count = int(data.get("esearchresult", {}).get("count", 0))
            articles = await self._fetch_summaries(ids[:max_results])
            return {
                "query": query,
                "total_found": count,
                "articles": articles,
                "pmids": ids,
            }
        except Exception as exc:
            logger.warning("PubMed search failed: %s", exc)
            return self._mock_results(query, max_results)

    async def _fetch_summaries(self, pmids: List[str]) -> List[Dict[str, Any]]:
        if not pmids:
            return []
        params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
        if settings.api_key:
            params["api_key"] = settings.api_key
        try:
            resp = await self.client.get(f"{settings.pubmed_base_url}/esummary.fcgi", params=params)
            resp.raise_for_status()
            data = resp.json()
            articles = []
            for pmid in pmids:
                article = data.get("result", {}).get(pmid, {})
                if article:
                    articles.append({
                        "pmid": pmid,
                        "title": article.get("title", ""),
                        "authors": [a.get("name", "") for a in article.get("authors", [])[:5]],
                        "journal": article.get("source", ""),
                        "pub_date": article.get("pubdate", ""),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    })
            return articles
        except Exception as exc:
            logger.warning("Summary fetch failed: %s", exc)
            return [{"pmid": p, "url": f"https://pubmed.ncbi.nlm.nih.gov/{p}/"} for p in pmids]

    def _mock_results(self, query: str, max_results: int) -> Dict[str, Any]:
        return {
            "query": query,
            "total_found": 0,
            "articles": [],
            "pmids": [],
            "note": "PubMed API unavailable, no results returned",
        }

    async def get_article(self, pmid: str) -> Dict[str, Any]:
        params = {"db": "pubmed", "id": pmid, "retmode": "json"}
        if settings.api_key:
            params["api_key"] = settings.api_key
        try:
            resp = await self.client.get(f"{settings.pubmed_base_url}/efetch.fcgi", params={**params, "rettype": "abstract"})
            resp.raise_for_status()
            return {"pmid": pmid, "content": resp.text, "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
        except Exception as exc:
            logger.warning("Article fetch failed: %s", exc)
            return {"pmid": pmid, "error": str(exc), "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
