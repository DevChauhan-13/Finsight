import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Attempt to import official Hindsight client
try:
    from hindsight_client import (
        Hindsight,
        RecallResponse,
        RecallResult,
        ReflectResponse,
        RetainResponse
    )
    HINDSIGHT_PACKAGE_AVAILABLE = True
except ImportError:
    HINDSIGHT_PACKAGE_AVAILABLE = False
    logger.warning("hindsight-client package not found. Using local fallback.")

class LocalFallbackMemoryStore:
    """
    In-memory fallback memory store adhering to the Hindsight retain/recall/reflect
    interface contract when the external Hindsight server is offline or unreachable.
    Allows automated unit tests and demo runs to operate seamlessly offline.
    """
    def __init__(self):
        # bank_id -> list of memory units
        self.banks: Dict[str, List[Dict[str, Any]]] = {}

    def retain(self, bank_id: str, content: str, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if bank_id not in self.banks:
            self.banks[bank_id] = []
        
        mem_id = f"mem_local_{len(self.banks[bank_id]) + 1}"
        record = {
            "id": mem_id,
            "text": content,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        self.banks[bank_id].append(record)
        return {"id": mem_id, "status": "retained", "bank_id": bank_id}

    def recall(self, bank_id: str, query: str, tags: Optional[List[str]] = None, max_results: int = 5) -> List[Dict[str, Any]]:
        bank = self.banks.get(bank_id, [])
        if not bank:
            return []
        
        query_words = set(query.lower().split())
        scored_results = []
        for mem in bank:
            mem_text = mem["text"].lower()
            mem_tags = [t.lower() for t in mem.get("tags", [])]
            
            # Simple keyword overlap scoring for local fallback
            text_matches = sum(1 for w in query_words if len(w) > 3 and w in mem_text)
            tag_matches = 0
            if tags:
                tag_matches = sum(2 for t in tags if any(t.lower() in mt for mt in mem_tags))
            
            score = text_matches + tag_matches
            if score > 0 or not query_words:
                scored_results.append((score, mem))
        
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_results[:max_results]]

    def reflect(self, bank_id: str, query: str, context: Optional[str] = None) -> str:
        recalls = self.recall(bank_id, query, max_results=5)
        if not recalls:
            return "No prior historical experience found in memory bank for this query."
        
        summaries = []
        for r in recalls:
            summaries.append(r["text"].strip())
        
        reflection = (
            f"Synthesized Operational Experience Across {len(recalls)} Case(s):\n"
            + "\n---\n".join(summaries[:3])
        )
        return reflection

    def clear(self, bank_id: Optional[str] = None):
        if bank_id:
            self.banks[bank_id] = []
        else:
            self.banks.clear()

class FinSightHindsightWrapper:
    """
    Production wrapper around the official Hindsight client API.
    Provides graceful degradation, automatic connection health checks,
    and fallback operation when the server is unavailable.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bank_id: Optional[str] = None
    ):
        self.base_url = base_url or os.environ.get("HINDSIGHT_API_URL", "http://localhost:8888")
        self.api_key = api_key or os.environ.get("HINDSIGHT_API_KEY", "")
        self.bank_id = bank_id or os.environ.get("HINDSIGHT_BANK_ID", "finsight-reconciliation")
        
        self.local_store = LocalFallbackMemoryStore()
        self.client: Optional[Any] = None
        self._is_server_connected: Optional[bool] = None

        if HINDSIGHT_PACKAGE_AVAILABLE:
            try:
                self.client = Hindsight(
                    base_url=self.base_url,
                    api_key=self.api_key if self.api_key else None,
                    timeout=2.0
                )
                import atexit
                atexit.register(self.close)
            except Exception as e:
                logger.warning(f"Could not initialize official Hindsight client: {e}")
                self.client = None

    def close(self):
        """Closes the official Hindsight client session cleanly."""
        if self.client and hasattr(self.client, "close"):
            try:
                self.client.close()
            except Exception:
                pass

    def check_connection(self) -> bool:
        """
        Pings Hindsight server to check connectivity.
        """
        if not self.client:
            self._is_server_connected = False
            return False
        
        try:
            # Try a lightweight check (get_version or recall empty)
            self.client.get_version()
            self._is_server_connected = True
            return True
        except Exception:
            self._is_server_connected = False
            return False

    @property
    def is_connected(self) -> bool:
        if self._is_server_connected is None:
            self._is_server_connected = self.check_connection()
        return self._is_server_connected

    def retain(
        self,
        content: str,
        bank_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Durable retention: Stores operational knowledge in Hindsight.
        """
        target_bank = bank_id or self.bank_id
        # Always record in local store as well for high-reliability fallback
        local_res = self.local_store.retain(target_bank, content, tags=tags, metadata=metadata)
        
        if self.is_connected and self.client:
            try:
                # Call official Hindsight retain
                resp = self.client.retain(
                    bank_id=target_bank,
                    content=content,
                    tags=tags,
                    metadata=metadata
                )
                return {
                    "status": "success",
                    "source": "hindsight_server",
                    "bank_id": target_bank,
                    "response": resp
                }
            except Exception as e:
                logger.warning(f"Official Hindsight retain call failed, using local: {e}")
        
        return {
            "status": "success",
            "source": "local_fallback",
            "bank_id": target_bank,
            "id": local_res["id"]
        }

    def recall(
        self,
        query: str,
        bank_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_tokens: int = 4096
    ) -> List[Dict[str, Any]]:
        """
        Context retrieval: Recalls relevant past experiences using TEMPR.
        """
        target_bank = bank_id or self.bank_id
        
        if self.is_connected and self.client:
            try:
                resp = self.client.recall(
                    bank_id=target_bank,
                    query=query,
                    tags=tags,
                    max_tokens=max_tokens
                )
                results = []
                if hasattr(resp, "results") and resp.results:
                    for r in resp.results:
                        results.append({
                            "id": getattr(r, "id", ""),
                            "text": getattr(r, "text", ""),
                            "tags": getattr(r, "tags", []),
                            "metadata": getattr(r, "metadata", {}) or {},
                            "type": getattr(r, "type", "experience")
                        })
                return results
            except Exception as e:
                logger.warning(f"Official Hindsight recall call failed, using local: {e}")
        
        # Fallback to local memory store
        return self.local_store.recall(target_bank, query, tags=tags)

    def reflect(
        self,
        query: str,
        bank_id: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Agentic reasoning & pattern synthesis across multiple memories.
        """
        target_bank = bank_id or self.bank_id
        
        if self.is_connected and self.client:
            try:
                resp = self.client.reflect(
                    bank_id=target_bank,
                    query=query,
                    context=context
                )
                if hasattr(resp, "text"):
                    return resp.text
                return str(resp)
            except Exception as e:
                logger.warning(f"Official Hindsight reflect call failed, using local: {e}")
        
        return self.local_store.reflect(target_bank, query, context=context)

    async def aretain(
        self,
        content: str,
        bank_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Async variant of retain."""
        return await asyncio.to_thread(self.retain, content, bank_id, tags, metadata)

    async def arecall(
        self,
        query: str,
        bank_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Async variant of recall."""
        return await asyncio.to_thread(self.recall, query, bank_id, tags)

    async def areflect(
        self,
        query: str,
        bank_id: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """Async variant of reflect."""
        return await asyncio.to_thread(self.reflect, query, bank_id, context)

    def clear_bank(self, bank_id: Optional[str] = None):
        """Clears memories for testing / reproducible demos."""
        target_bank = bank_id or self.bank_id
        self.local_store.clear(target_bank)
        if self.is_connected and self.client:
            try:
                self.client.delete_bank(bank_id=target_bank)
            except Exception:
                pass
