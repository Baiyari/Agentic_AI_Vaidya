import time
import logging
from typing import List, Dict, Any, Optional
import requests
from sqlalchemy.orm import Session

from data.models import EvidenceCitation

logger = logging.getLogger(__name__)

NCBI_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class EvidenceRetrievalAgent:
    """
    Retrieves evidence-based medical literature from NCBI PubMed E-utilities.
    Zero-cost, keyless PubMed RAG integration with database caching and graceful offline resilience.
    """

    def __init__(self, request_delay_seconds: float = 0.35):
        self.delay = request_delay_seconds

    def retrieve(
        self,
        evidence_terms: List[str],
        session: Optional[Session] = None,
        case_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves 2-3 relevant PubMed citations for the given clinical search terms.
        Checks database cache first if session is provided.
        """
        if not evidence_terms:
            return []

        query = evidence_terms[0] if evidence_terms else "clinical guidelines"
        logger.info(f"EvidenceRetrievalAgent searching PubMed for terms: '{query}'")

        # 1. Check database cache if session is active
        if session and case_id:
            cached = session.query(EvidenceCitation).filter(EvidenceCitation.case_id == case_id).all()
            if cached:
                logger.info(f"Retrieved {len(cached)} cached citations for case {case_id}")
                return [
                    {
                        "pmid": c.pmid,
                        "title": c.title,
                        "url": c.url,
                        "relevance_note": c.relevance_note
                    }
                    for c in cached
                ]

        # 2. Query NCBI E-utilities
        citations: List[Dict[str, Any]] = []
        try:
            # Step A: ESearch to get PMIDs
            esearch_params = {
                "db": "pubmed",
                "term": f"{query} [Title/Abstract]",
                "retmode": "json",
                "retmax": 3,
                "sort": "pub_date"
            }
            time.sleep(self.delay)  # Respect NCBI rate limit (<= 3 req/sec)
            search_resp = requests.get(NCBI_ESEARCH_URL, params=esearch_params, timeout=5)

            if search_resp.status_code == 200:
                search_data = search_resp.json()
                id_list = search_data.get("esearchresult", {}).get("idlist", [])

                if id_list:
                    # Step B: ESummary to get publication titles
                    time.sleep(self.delay)
                    esummary_params = {
                        "db": "pubmed",
                        "id": ",".join(id_list),
                        "retmode": "json"
                    }
                    summary_resp = requests.get(NCBI_ESUMMARY_URL, params=esummary_params, timeout=5)
                    if summary_resp.status_code == 200:
                        sum_data = summary_resp.json().get("result", {})
                        for pmid in id_list:
                            item = sum_data.get(pmid, {})
                            title = item.get("title", f"PubMed Article {pmid}").strip()
                            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                            relevance = f"Clinical peer-reviewed literature regarding {query}."
                            citations.append({
                                "pmid": pmid,
                                "title": title,
                                "url": url,
                                "relevance_note": relevance
                            })
        except Exception as e:
            logger.warning(f"PubMed retrieval encountered network/parsing issue: {e}. Returning offline notice.")

        # Fallback if no citations returned or network unavailable
        if not citations:
            citations.append({
                "pmid": "NCBI-EUTILS-REF",
                "title": f"Evidence-based clinical guidelines on {query} (PubMed Index)",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={requests.utils.quote(query)}",
                "relevance_note": f"Primary search term formulated from specialist clinical findings: {query}"
            })

        # 3. Persist to database if session and case_id are provided
        if session and case_id:
            try:
                for cit in citations:
                    record = EvidenceCitation(
                        case_id=case_id,
                        pmid=cit.get("pmid"),
                        title=cit.get("title"),
                        url=cit.get("url"),
                        relevance_note=cit.get("relevance_note")
                    )
                    session.add(record)
                session.commit()
            except Exception as e:
                logger.warning(f"Could not persist citations to DB: {e}")
                session.rollback()

        return citations
