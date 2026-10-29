"""
Validation tests for Pagination and Caching layers.
"""
import unittest
import time
from backend.pagination import Paginator, PaginationError
from backend.storage import CacheManager


class TestPaginationValidation(unittest.TestCase):
    def setUp(self):
        self.sample_items = [f"Item-{i}" for i in range(1, 36)]  # 35 items

    def test_pagination_page_one(self):
        res = Paginator.paginate(self.sample_items, page=1, page_size=10)
        self.assertEqual(res["page"], 1)
        self.assertEqual(res["page_size"], 10)
        self.assertEqual(res["total_items"], 35)
        self.assertEqual(res["total_pages"], 4)
        self.assertTrue(res["has_next"])
        self.assertFalse(res["has_prev"])
        self.assertEqual(len(res["items"]), 10)
        self.assertEqual(res["items"][0], "Item-1")
        self.assertEqual(res["items"][-1], "Item-10")

    def test_pagination_last_page(self):
        res = Paginator.paginate(self.sample_items, page=4, page_size=10)
        self.assertEqual(res["page"], 4)
        self.assertFalse(res["has_next"])
        self.assertTrue(res["has_prev"])
        self.assertEqual(len(res["items"]), 5)  # Remaining 5 items
        self.assertEqual(res["items"][-1], "Item-35")

    def test_pagination_page_out_of_bounds(self):
        # When page > total_pages, items should be empty
        res = Paginator.paginate(self.sample_items, page=5, page_size=10)
        self.assertEqual(res["items"], [])
        self.assertFalse(res["has_next"])
        self.assertTrue(res["has_prev"])

    def test_pagination_invalid_page_number(self):
        with self.assertRaises(PaginationError):
            Paginator.paginate(self.sample_items, page=0, page_size=10)
        with self.assertRaises(PaginationError):
            Paginator.paginate(self.sample_items, page=-1, page_size=10)

    def test_pagination_excessive_page_size(self):
        with self.assertRaises(PaginationError):
            Paginator.paginate(self.sample_items, page=1, page_size=101)


class TestCacheValidation(unittest.TestCase):
    def setUp(self):
        self.cache = CacheManager(default_ttl_seconds=1)

    def test_cache_set_and_hit(self):
        self.cache.set("key1", {"value": 100})
        val = self.cache.get("key1")
        self.assertEqual(val, {"value": 100})
        self.assertEqual(self.cache.hits, 1)
        self.assertEqual(self.cache.misses, 0)

    def test_cache_miss(self):
        val = self.cache.get("non_existent")
        self.assertIsNone(val)
        self.assertEqual(self.cache.misses, 1)

    def test_cache_expiration(self):
        self.cache.set("temp_key", "temporary", ttl_seconds=1)
        self.assertEqual(self.cache.get("temp_key"), "temporary")
        time.sleep(1.1)  # wait for expiration
        self.assertIsNone(self.cache.get("temp_key"))

    def test_cache_invalidation(self):
        self.cache.set("act:criminal", "data1")
        self.cache.set("act:civil", "data2")
        self.cache.set("search:criminal", "results")

        removed = self.cache.invalidate("act:")
        self.assertEqual(removed, 2)
        self.assertIsNone(self.cache.get("act:criminal"))
        self.assertIsNone(self.cache.get("act:civil"))
        self.assertEqual(self.cache.get("search:criminal"), "results")

    def test_cache_stats(self):
        self.cache.set("k1", "v1")
        self.cache.get("k1")  # Hit
        self.cache.get("k2")  # Miss
        stats = self.cache.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["total_requests"], 2)
        self.assertEqual(stats["hit_ratio"], 0.5)


if __name__ == "__main__":
    unittest.main()
