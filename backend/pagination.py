"""
Pagination helper and validation.
"""
import math
from typing import List, Dict, Any


class PaginationError(Exception):
    pass


class Paginator:
    @staticmethod
    def paginate(items: List[Any], page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Paginates a list of items with rigorous boundary validation.
        """
        if not isinstance(page, int) or page < 1:
            raise PaginationError("Page number must be an integer >= 1.")
        if not isinstance(page_size, int) or page_size < 1:
            raise PaginationError("Page size must be an integer >= 1.")
        if page_size > 100:
            raise PaginationError("Page size cannot exceed 100.")

        total_items = len(items)
        total_pages = max(1, math.ceil(total_items / page_size))

        if page > total_pages and total_items > 0:
            paged_items = []
        else:
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paged_items = items[start_idx:end_idx]

        return {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "items": paged_items
        }
