"""
Firebase collections module.

This module provides generic base classes and examples for working with
Firebase Firestore collections.
"""

from ryutils.firebase.collections.base import (
    Changes,
    CollectionConfig,
    CollectionConfigDict,
    FirebaseCollection,
)

__all__ = [
    "Changes",
    "CollectionConfig",
    "CollectionConfigDict",
    "FirebaseCollection",
]
