"""
Storage repository, duplicate validations, and caching layer for Legal Hub.
"""
import os
import json
import time
from typing import Dict, List, Optional, Any
from backend.models import Act, Article, Attachment, ValidationError


class StorageError(Exception):
    pass


class CacheManager:
    """
    In-memory caching mechanism with TTL and hit/miss tracking for cache validation.
    """
    def __init__(self, default_ttl_seconds: int = 300):
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry["expires_at"]:
                self.hits += 1
                return entry["data"]
            else:
                del self._cache[key]
        self.misses += 1
        return None

    def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        self._cache[key] = {
            "data": data,
            "expires_at": time.time() + ttl
        }

    def invalidate(self, key_prefix: Optional[str] = None) -> int:
        if not key_prefix:
            count = len(self._cache)
            self._cache.clear()
            return count
        keys_to_remove = [k for k in self._cache if k.startswith(key_prefix)]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_ratio = (self.hits / total) if total > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_ratio": round(hit_ratio, 4),
            "cached_entries": len(self._cache)
        }


class LegalStorage:
    def __init__(self, acts_dir: str):
        self.acts_dir = acts_dir
        self.acts: Dict[str, Act] = {}
        self.cache = CacheManager()
        self.load_all_acts()

    def load_all_acts(self) -> None:
        """
        Loads all acts from JSON files and validates duplicates.
        """
        self.acts.clear()
        self.cache.invalidate()

        if not os.path.exists(self.acts_dir):
            return

        for filename in sorted(os.listdir(self.acts_dir)):
            if filename.endswith(".json"):
                filepath = os.path.join(self.acts_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.add_act(data)

    def add_act(self, data: Dict[str, Any]) -> Act:
        """
        Validates and adds an act. Raises StorageError if duplicate act ID or duplicate act name exists.
        """
        act_id = data.get("id", "").strip()
        act_name = data.get("name", "").strip()

        if not act_id:
            raise ValidationError("Act ID is required.")

        # Duplicate act ID validation
        if act_id in self.acts:
            raise StorageError(f"Duplicate act ID '{act_id}' is already registered.")

        # Duplicate act name validation
        for existing in self.acts.values():
            if existing.name == act_name:
                raise StorageError(f"Duplicate act name '{act_name}' is already registered.")

        # Construct and validate Act (which checks internal duplicate articles and attachments)
        act = Act(**data)
        self.acts[act.id] = act
        self.cache.invalidate(f"act:{act.id}")
        return act

    def get_act(self, act_id: str) -> Optional[Act]:
        cache_key = f"act:{act_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        act = self.acts.get(act_id)
        if act:
            self.cache.set(cache_key, act)
        return act

    def list_acts(self) -> List[Dict[str, Any]]:
        cache_key = "acts:list"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        result = [act.to_dict(include_articles=False) for act in self.acts.values()]
        self.cache.set(cache_key, result)
        return result

    def get_article(self, act_id: str, article_no: str) -> Optional[Article]:
        act = self.get_act(act_id)
        if not act:
            return None
        return act.articles_map.get(str(article_no).strip())

    def search_articles(self, act_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Searches articles in an act by number, title, content, legislative reasons, or practical insights.
        """
        act = self.get_act(act_id)
        if not act:
            return []

        q = (query or "").strip().lower()
        if not q:
            return [art.to_dict() for art in act.articles]

        cache_key = f"search:{act_id}:{q}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        results = []
        for art in act.articles:
            # Check match by exact or partial article number
            match_no = q == art.article_no.lower() or f"第{q}條" in f"第{art.article_no}條"
            match_title = q in art.title.lower()
            match_content = q in art.content.lower()
            match_reasons = q in art.legislative_reasons.lower()
            match_insights = any(
                q in item.get("summary", "").lower() or q in item.get("ref", "").lower()
                for item in art.practical_insights
            )

            if match_no or match_title or match_content or match_reasons or match_insights:
                results.append(art.to_dict())

        self.cache.set(cache_key, results)
        return results
