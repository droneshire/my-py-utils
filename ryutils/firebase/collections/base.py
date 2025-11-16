"""
Generic base class for Firebase collections.

This module provides a generic base class for working with Firebase Firestore collections.
It handles common operations like caching, watching, and syncing with Firestore.
"""

import abc
import copy
import enum
import json
import threading
import typing as T
from pathlib import Path

import deepdiff
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_document import DocumentSnapshot
from google.cloud.firestore_v1.collection import CollectionReference
from google.cloud.firestore_v1.watch import DocumentChange, Watch

from ryutils import log
from ryutils.verbose import Verbose


class Changes(enum.Enum):
    """Enumeration for document change types."""

    ADDED = 1
    MODIFIED = 2
    REMOVED = 3


class CollectionConfig(T.TypedDict, total=False):
    """
    Configuration for a single collection.

    All fields are optional. This allows for flexible configuration
    where collections can specify only the options they need.
    """

    null_document: T.Dict[str, T.Any]
    snapshot_handler: T.Union[T.Callable[[T.List[DocumentSnapshot]], None], str]
    update_handler: T.Callable[[str, str, T.Any], None]


CollectionConfigDict = T.Dict[str, CollectionConfig]
"""Type alias for a dictionary mapping collection names to their configurations."""


class FirebaseCollection(abc.ABC):
    """
    Generic base class for Firebase Firestore collections.

    This class provides common functionality for:
    - Cache management with thread-safe locks
    - Real-time watchers for collection changes
    - Snapshot handling and diff computation
    - Uploading/updating documents to Firestore

    Subclasses should implement:
    - Collection name(s)
    - Data type definitions
    - Collection-specific handlers

    Alternatively, can be configured with a collections list and config dict
    for generic behavior without subclassing.
    """

    def __init__(
        self,
        credentials_file: Path,
        verbose: Verbose,
        auto_init: bool = True,
        database_id: T.Optional[str] = None,
        collections: T.Optional[T.List[str]] = None,
        config: T.Optional[CollectionConfigDict] = None,
    ) -> None:
        """
        Initialize the Firebase collection.

        Args:
            credentials_file: Path to Firebase credentials JSON file
            verbose: Verbose configuration object
            auto_init: Whether to automatically initialize watchers
            database_id: Optional Firestore database ID (defaults to default database)
            collections: Optional list of collection names (for generic usage)
            config: Optional configuration dict mapping collection names to their configs
        """
        self.credentials_file = credentials_file
        self.verbose = verbose
        self.auto_init = auto_init
        self.database_id = database_id
        self.collections: CollectionConfigDict = config or {}
        self._collection_names: T.Optional[T.List[str]] = collections

        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:  # pylint: disable=protected-access
            auth = credentials.Certificate(str(credentials_file))
            firebase_admin.initialize_app(auth)

        # Initialize Firestore client with optional database_id
        if database_id:
            self.database = firestore.client(database_id=database_id)
        else:
            self.database = firestore.client()

        # Get collection references from subclass or from collections list
        self.collection_refs: T.Dict[str, CollectionReference] = self._get_collection_refs()

        # Watchers for each collection
        self.watchers: T.Dict[str, T.Optional[Watch]] = {
            name: None for name in self.collection_refs.keys()
        }

        # Cache for each collection (type defined by subclass)
        self.caches: T.Dict[str, T.Any] = self._initialize_caches()

        # Thread synchronization
        self.callback_done: threading.Event = threading.Event()
        self.cache_locks: T.Dict[str, threading.RLock] = {
            name: threading.RLock() for name in self.collection_refs.keys()
        }

        if self.auto_init:
            self.init()

    def _get_collection_names(self) -> T.List[str]:
        """
        Get the list of collection names this class manages.

        Returns:
            List of collection name strings
        """
        if self._collection_names is not None:
            return self._collection_names
        # Fallback to abstract method for subclasses
        return self._get_collection_names_impl()

    @abc.abstractmethod
    def _get_collection_names_impl(self) -> T.List[str]:
        """
        Get the list of collection names this class manages (subclass implementation).

        Returns:
            List of collection name strings
        """

    def _get_collection_refs(self) -> T.Dict[str, CollectionReference]:
        """
        Get collection references for all managed collections.

        Returns:
            Dictionary mapping collection names to CollectionReference objects
        """
        if self._collection_names is not None:
            return {name: self.database.collection(name) for name in self._collection_names}
        # Fallback to abstract method for subclasses
        return self._get_collection_refs_impl()

    @abc.abstractmethod
    def _get_collection_refs_impl(self) -> T.Dict[str, CollectionReference]:
        """
        Get collection references for all managed collections (subclass implementation).

        Returns:
            Dictionary mapping collection names to CollectionReference objects
        """

    def _initialize_caches(self) -> T.Dict[str, T.Any]:
        """
        Initialize empty caches for all collections.

        Returns:
            Dictionary mapping collection names to empty cache structures
        """
        if self._collection_names is not None:
            return {name: {} for name in self._collection_names}
        # Fallback to abstract method for subclasses
        return self._initialize_caches_impl()

    @abc.abstractmethod
    def _initialize_caches_impl(self) -> T.Dict[str, T.Any]:
        """
        Initialize empty caches for all collections (subclass implementation).

        Returns:
            Dictionary mapping collection names to empty cache structures
        """

    def _get_null_document(self, collection_name: str) -> T.Any:
        """
        Get a null/empty document template for a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Null document template
        """
        # Check if config provides null_document
        if collection_name in self.collections:
            collection_config = self.collections[collection_name]
            if "null_document" in collection_config:
                return copy.deepcopy(collection_config["null_document"])
        # Fallback to abstract method for subclasses
        return self._get_null_document_impl(collection_name)

    @abc.abstractmethod
    def _get_null_document_impl(self, collection_name: str) -> T.Any:
        """
        Get a null/empty document template for a collection (subclass implementation).

        Args:
            collection_name: Name of the collection

        Returns:
            Null document template
        """

    def _handle_collection_snapshot(
        self, collection_name: str, collection_snapshot: T.List[DocumentSnapshot]
    ) -> None:
        """
        Handle a collection snapshot update.

        Args:
            collection_name: Name of the collection
            collection_snapshot: List of document snapshots
        """
        # Check if config provides snapshot_handler
        if collection_name in self.collections:
            collection_config = self.collections[collection_name]
            if "snapshot_handler" in collection_config:
                handler = collection_config["snapshot_handler"]
                if callable(handler):
                    handler(collection_snapshot)
                    return
        # Fallback to abstract method for subclasses
        self._handle_collection_snapshot_impl(collection_name, collection_snapshot)

    @abc.abstractmethod
    def _handle_collection_snapshot_impl(
        self, collection_name: str, collection_snapshot: T.List[DocumentSnapshot]
    ) -> None:
        """
        Handle a collection snapshot update (subclass implementation).

        Args:
            collection_name: Name of the collection
            collection_snapshot: List of document snapshots
        """

    def _handle_document_update(self, collection_name: str, doc_id: str, doc_data: T.Any) -> None:
        """
        Handle a document update for a specific collection.

        Args:
            collection_name: Name of the collection
            doc_id: Document ID
            doc_data: Document data
        """
        # Check if config provides update_handler
        if collection_name in self.collections:
            collection_config = self.collections[collection_name]
            if "update_handler" in collection_config:
                handler = collection_config["update_handler"]
                if callable(handler):
                    handler(collection_name, doc_id, doc_data)
                    return
        # Fallback to abstract method for subclasses
        self._handle_document_update_impl(collection_name, doc_id, doc_data)

    @abc.abstractmethod
    def _handle_document_update_impl(
        self, collection_name: str, doc_id: str, doc_data: T.Any
    ) -> None:
        """
        Handle a document update for a specific collection (subclass implementation).

        Args:
            collection_name: Name of the collection
            doc_id: Document ID
            doc_data: Document data
        """

    def init(self) -> None:
        """Initialize watchers for all collections."""
        for collection_name, collection_ref in self.collection_refs.items():
            # Use a factory function to capture collection_name correctly
            def make_handler(name: str) -> T.Callable:
                def handler(
                    snapshots: T.List[DocumentSnapshot],
                    changes: T.List[DocumentChange],
                    read_time: T.Any,
                ) -> None:
                    return self._collection_snapshot_handler(snapshots, changes, read_time, name)

                return handler

            self.watchers[collection_name] = collection_ref.on_snapshot(
                make_handler(collection_name)
            )

    def _collection_snapshot_handler(
        self,
        collection_snapshot: T.List[DocumentSnapshot],
        changed_docs: T.List[DocumentChange],
        read_time: T.Any,  # pylint: disable=unused-argument
        collection_name: str,
    ) -> None:
        """
        Generic handler for collection snapshots.

        Args:
            collection_snapshot: List of document snapshots
            changed_docs: List of document changes
            read_time: Read timestamp
            collection_name: Name of the collection
        """
        try:
            log.print_warn(
                f"Received collection `{collection_name}` snapshot "
                f"for {len(collection_snapshot)} documents"
            )

            # Call collection-specific handler
            self._handle_collection_snapshot(collection_name, collection_snapshot)

            # Log document changes
            for change in changed_docs:
                doc_id = change.document.id
                if change.type.name == Changes.ADDED.name:
                    log.print_ok_blue(f"Added document: {doc_id}")
                elif change.type.name == Changes.MODIFIED.name:
                    log.print_ok_blue(f"Modified document: {doc_id}")
                elif change.type.name == Changes.REMOVED.name:
                    log.print_ok_blue(f"Removed document: {doc_id}")

            self.callback_done.set()
        except Exception as e:  # pylint: disable=broad-except
            log.print_fail(f"Error handling collection snapshot for {collection_name}: {e}")

    def _delete_document(self, collection_name: str, doc_id: str) -> None:
        """
        Delete a document from the cache.

        Args:
            collection_name: Name of the collection
            doc_id: Document ID to delete
        """
        with self.cache_locks[collection_name]:
            if doc_id in self.caches[collection_name]:
                del self.caches[collection_name][doc_id]
        log.print_warn(f"Deleting {collection_name} document {doc_id}")

    def _maybe_upload_to_firestore(
        self,
        collection_name: str,
        doc_id: str,
        old_doc: T.Any,
        new_doc: T.Any,
        merge: bool = False,
    ) -> None:
        """
        Upload document to Firestore if there are differences.

        Args:
            collection_name: Name of the collection
            doc_id: Document ID
            old_doc: Old document data
            new_doc: New document data
            merge: Whether to merge with existing document (default: False)
        """
        diff = deepdiff.DeepDiff(old_doc, new_doc, ignore_order=True)
        if not diff:
            return

        diff_json = diff.to_json()
        diff_dict = json.dumps(json.loads(diff_json), indent=4, sort_keys=True)
        log.print_normal(f"Updated {doc_id} in {collection_name}:\n{diff_dict}")

        doc_dict_firestore = json.loads(json.dumps(new_doc))
        collection_ref = self.collection_refs[collection_name]

        try:
            collection_ref.document(doc_id).set(doc_dict_firestore, merge=merge)
        except KeyboardInterrupt as exc:
            raise KeyboardInterrupt from exc
        except Exception as e:  # pylint: disable=broad-except
            log.print_warn(f"Failed to update {doc_id} in {collection_name}: {e}")

    def _print_document_diff(
        self, collection_name: str, doc_id: str, old_doc: T.Any, new_doc: T.Any
    ) -> None:
        """
        Print document diff if verbose mode is enabled.

        Args:
            collection_name: Name of the collection
            doc_id: Document ID
            old_doc: Old document data
            new_doc: New document data
        """
        if self.verbose.general:
            log.print_normal(f"{json.dumps(new_doc, indent=4, sort_keys=True)}")

        if not self.verbose.firebase:
            return

        diff = deepdiff.DeepDiff(old_doc, new_doc, ignore_order=True)

        if diff:
            try:
                diff_json = diff.to_json()
                # hack b/c of https://github.com/seperman/deepdiff/issues/490
                diff_json_sorted = json.dumps(json.loads(diff_json), indent=4, sort_keys=True)
                log.print_normal(f"Diff for {doc_id} in {collection_name}:\n{diff_json_sorted}")
            except Exception as exc:  # pylint: disable=broad-except
                log.print_fail(f"Failed to print diff for {doc_id}: {exc}\n{diff}")
        else:
            log.print_normal(f"No diff for {doc_id} in {collection_name}")

    def get_cache(self, collection_name: str) -> T.Any:
        """
        Get a thread-safe copy of the cache for a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Deep copy of the cache
        """
        with self.cache_locks[collection_name]:
            return copy.deepcopy(self.caches[collection_name])

    def update_watchers(self, collection_name: T.Optional[str] = None) -> None:
        """
        Update watchers for collection(s).

        Args:
            collection_name: Specific collection to update, or None for all
        """
        log.print_normal("Updating watcher...")
        collections_to_update = (
            [collection_name] if collection_name else self.collection_refs.keys()
        )

        for name in collections_to_update:
            if self.watchers[name]:
                self.watchers[name].unsubscribe()  # type: ignore

            # Use a factory function to capture collection name correctly
            def make_handler(coll_name: str) -> T.Callable:
                def handler(
                    snapshots: T.List[DocumentSnapshot],
                    changes: T.List[DocumentChange],
                    read_time: T.Any,
                ) -> None:
                    return self._collection_snapshot_handler(
                        snapshots, changes, read_time, coll_name
                    )

                return handler

            self.watchers[name] = self.collection_refs[name].on_snapshot(make_handler(name))

    def update_from_firestore(self, collection_name: str) -> None:
        """
        Synchronously update from Firestore database.

        Args:
            collection_name: Name of the collection to update
        """
        log.print_warn(f"Updating {collection_name} from firestore database instead of cache")
        doc_ids = list(self.caches[collection_name].keys())

        with self.cache_locks[collection_name]:
            self.caches[collection_name] = {}
            for doc in self.collection_refs[collection_name].list_documents():
                self.caches[collection_name][doc.id] = doc.get().to_dict()

        for doc_id in doc_ids:
            if doc_id not in self.caches[collection_name]:
                self._delete_document(collection_name, doc_id)

        self.callback_done.set()

    def check_and_maybe_update_to_firestore(
        self,
        collection_name: str,
        doc_id: str,
        doc_data: T.Any,
        ignore_missing: bool = False,
    ) -> None:
        """
        Check and maybe update a document to Firestore.

        Args:
            collection_name: Name of the collection
            doc_id: Document ID
            doc_data: Document data
            ignore_missing: Whether to ignore if document doesn't exist in cache
        """
        if doc_id not in self.caches[collection_name] and not ignore_missing:
            return

        old_doc = copy.deepcopy(self.caches[collection_name].get(doc_id, {}))

        if not old_doc and not ignore_missing:
            return

        self._maybe_upload_to_firestore(collection_name, doc_id, old_doc, doc_data)

    def check_and_maybe_handle_updates(self) -> None:
        """Check for updates and handle them if callback is done."""
        if self.callback_done.is_set():
            self.callback_done.clear()
            log.print_bright("Handling firestore database updates")

            for collection_name, cache in self.caches.items():
                for doc_id, doc_data in cache.items():
                    self._handle_document_update(collection_name, doc_id, doc_data)

    def to_firebase(self) -> None:
        """
        Perform periodic updates to Firebase.

        Default implementation is a no-op. Subclasses can override to implement
        periodic tasks like health pings or author updates.
        """
