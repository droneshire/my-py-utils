"""
Tests for Firebase module generic components.

This module tests the generic Firebase collection and manager functionality
without requiring actual Firebase connections.
"""

import typing as T
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from google.cloud.firestore_v1.base_document import DocumentSnapshot
from google.cloud.firestore_v1.collection import CollectionReference

from ryutils.firebase.collections import CollectionConfig, CollectionConfigDict, FirebaseCollection
from ryutils.firebase.collections.base import Changes
from ryutils.firebase.firebase_manager import CollectionConfig as ManagerCollectionConfig
from ryutils.firebase.firebase_manager import FirebaseManager
from ryutils.verbose import Verbose


class MockChannels:
    """Mock channels object for testing."""

    CONFIG_CHANNEL = "config_channel"


channels = MockChannels()


class ConfigMessagePb:
    """Mock protobuf message type for testing."""

    def __init__(self) -> None:
        """Initialize mock protobuf message."""

    def SerializeToString(self) -> bytes:
        """Serialize message to bytes."""
        return b""


class MockFirebaseCollection(FirebaseCollection):
    """Mock Firebase collection for testing."""

    def _get_collection_names_impl(self) -> list[str]:
        """Return test collection names."""
        return ["test_collection"]

    def _get_collection_refs_impl(self) -> dict[str, Mock]:  # type: ignore[override]
        """Return mock collection references."""
        mock_ref = Mock(spec=CollectionReference)
        mock_ref.on_snapshot = Mock(return_value=None)
        return {"test_collection": mock_ref}  # type: ignore[return-value]

    def _initialize_caches_impl(self) -> dict[str, dict[str, dict]]:
        """Initialize empty caches."""
        return {"test_collection": {}}

    def _get_null_document_impl(self, collection_name: str) -> dict:
        """Return null document template."""
        return {"id": "", "data": ""}

    def _handle_collection_snapshot_impl(
        self, collection_name: str, collection_snapshot: list[DocumentSnapshot]
    ) -> None:
        """Handle collection snapshot updates."""
        # Default implementation for testing

    def _handle_document_update_impl(
        self, collection_name: str, doc_id: str, doc_data: dict
    ) -> None:
        """Handle document updates."""
        # Default implementation for testing


class TestCollectionConfig(unittest.TestCase):
    """Test CollectionConfig TypedDict."""

    def test_collection_config_creation(self) -> None:
        """Test creating a CollectionConfig."""
        config: CollectionConfig = {
            "null_document": {"id": "", "name": ""},
        }
        self.assertIn("null_document", config)
        self.assertEqual(config["null_document"]["id"], "")

    def test_collection_config_with_handlers(self) -> None:
        """Test CollectionConfig with handlers."""

        def snapshot_handler(
            snapshots: list[DocumentSnapshot],  # pylint: disable=unused-argument
        ) -> None:
            """Snapshot handler for testing."""

        def update_handler(
            collection_name: str,  # pylint: disable=unused-argument
            doc_id: str,  # pylint: disable=unused-argument
            doc_data: dict,  # pylint: disable=unused-argument
        ) -> None:
            """Update handler for testing."""

        config: CollectionConfig = {
            "null_document": {"id": ""},
            "snapshot_handler": snapshot_handler,
            "update_handler": update_handler,
        }
        self.assertIn("snapshot_handler", config)
        self.assertIn("update_handler", config)
        self.assertTrue(callable(config["snapshot_handler"]))
        self.assertTrue(callable(config["update_handler"]))

    def test_collection_config_dict(self) -> None:
        """Test CollectionConfigDict."""
        config: CollectionConfigDict = {
            "collection1": {
                "null_document": {"id": ""},
            },
            "collection2": {
                "null_document": {"id": "", "data": ""},
            },
        }
        self.assertEqual(len(config), 2)
        self.assertIn("collection1", config)
        self.assertIn("collection2", config)


class TestFirebaseCollection(unittest.TestCase):
    """Test FirebaseCollection base class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.credentials_file = Path("/tmp/test_credentials.json")
        self.verbose = Verbose()
        self.collections = ["test_collection"]
        self.config: CollectionConfigDict = {
            "test_collection": {
                "null_document": {"id": "", "data": ""},
            },
        }

    @patch("ryutils.firebase.collections.base.firebase_admin._apps", [])
    @patch("ryutils.firebase.collections.base.firebase_admin.initialize_app")
    @patch("ryutils.firebase.collections.base.credentials.Certificate")
    @patch("ryutils.firebase.collections.base.firestore.client")
    def test_collection_initialization_with_collections(
        self, mock_client: Mock, mock_cert: Mock, mock_init: Mock  # pylint: disable=unused-argument
    ) -> None:
        """Test collection initialization with collections parameter."""
        mock_db = Mock()
        mock_collection_ref = Mock()
        mock_collection_ref.on_snapshot = Mock(return_value=None)
        mock_db.collection = Mock(return_value=mock_collection_ref)
        mock_client.return_value = mock_db

        collection = MockFirebaseCollection(
            credentials_file=self.credentials_file,
            verbose=self.verbose,
            collections=self.collections,
            config=self.config,
            auto_init=False,
        )

        self.assertEqual(
            collection._collection_names,  # pylint: disable=protected-access
            self.collections,
        )
        self.assertIn("test_collection", collection.collection_refs)
        self.assertIn("test_collection", collection.caches)

    @patch("ryutils.firebase.collections.base.firebase_admin._apps", [])
    @patch("ryutils.firebase.collections.base.firebase_admin.initialize_app")
    @patch("ryutils.firebase.collections.base.credentials.Certificate")
    @patch("ryutils.firebase.collections.base.firestore.client")
    def test_get_collection_names(
        self, mock_client: Mock, mock_cert: Mock, mock_init: Mock  # pylint: disable=unused-argument
    ) -> None:
        """Test getting collection names."""
        mock_db = Mock()
        mock_collection_ref = Mock()
        mock_collection_ref.on_snapshot = Mock(return_value=None)
        mock_db.collection = Mock(return_value=mock_collection_ref)
        mock_client.return_value = mock_db

        collection = MockFirebaseCollection(
            credentials_file=self.credentials_file,
            verbose=self.verbose,
            collections=self.collections,
            auto_init=False,
        )

        names = collection._get_collection_names()  # pylint: disable=protected-access
        self.assertEqual(names, self.collections)

    @patch("ryutils.firebase.collections.base.firebase_admin._apps", [])
    @patch("ryutils.firebase.collections.base.firebase_admin.initialize_app")
    @patch("ryutils.firebase.collections.base.credentials.Certificate")
    @patch("ryutils.firebase.collections.base.firestore.client")
    def test_get_null_document_from_config(
        self, mock_client: Mock, mock_cert: Mock, mock_init: Mock  # pylint: disable=unused-argument
    ) -> None:
        """Test getting null document from config."""
        mock_db = Mock()
        mock_collection_ref = Mock()
        mock_collection_ref.on_snapshot = Mock(return_value=None)
        mock_db.collection = Mock(return_value=mock_collection_ref)
        mock_client.return_value = mock_db

        null_doc = {"id": "", "custom": "value"}
        config: CollectionConfigDict = {
            "test_collection": {
                "null_document": null_doc,
            },
        }

        collection = MockFirebaseCollection(
            credentials_file=self.credentials_file,
            verbose=self.verbose,
            collections=self.collections,
            config=config,
            auto_init=False,
        )

        result = collection._get_null_document(  # pylint: disable=protected-access
            "test_collection"
        )
        self.assertEqual(result, null_doc)
        # Should be a deep copy
        self.assertIsNot(result, null_doc)

    @patch("ryutils.firebase.collections.base.firebase_admin._apps", [])
    @patch("ryutils.firebase.collections.base.firebase_admin.initialize_app")
    @patch("ryutils.firebase.collections.base.credentials.Certificate")
    @patch("ryutils.firebase.collections.base.firestore.client")
    def test_get_cache(
        self, mock_client: Mock, mock_cert: Mock, mock_init: Mock  # pylint: disable=unused-argument
    ) -> None:
        """Test getting cache."""
        mock_db = Mock()
        mock_collection_ref = Mock()
        mock_collection_ref.on_snapshot = Mock(return_value=None)
        mock_db.collection = Mock(return_value=mock_collection_ref)
        mock_client.return_value = mock_db

        collection = MockFirebaseCollection(
            credentials_file=self.credentials_file,
            verbose=self.verbose,
            collections=self.collections,
            auto_init=False,
        )

        # Add some test data
        collection.caches["test_collection"]["doc1"] = {"id": "doc1", "data": "test"}

        cache = collection.get_cache("test_collection")
        self.assertEqual(cache["doc1"]["data"], "test")
        # Should be a deep copy
        self.assertIsNot(cache, collection.caches["test_collection"])

    @patch("ryutils.firebase.collections.base.firebase_admin._apps", [])
    @patch("ryutils.firebase.collections.base.firebase_admin.initialize_app")
    @patch("ryutils.firebase.collections.base.credentials.Certificate")
    @patch("ryutils.firebase.collections.base.firestore.client")
    def test_to_firebase(
        self, mock_client: Mock, mock_cert: Mock, mock_init: Mock  # pylint: disable=unused-argument
    ) -> None:
        """Test to_firebase method."""
        mock_db = Mock()
        mock_collection_ref = Mock()
        mock_collection_ref.on_snapshot = Mock(return_value=None)
        mock_db.collection = Mock(return_value=mock_collection_ref)
        mock_client.return_value = mock_db

        collection = MockFirebaseCollection(
            credentials_file=self.credentials_file,
            verbose=self.verbose,
            collections=self.collections,
            auto_init=False,
        )

        # Should not raise
        collection.to_firebase()


class TestFirebaseManager(unittest.TestCase):
    """Test FirebaseManager."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.verbose = Verbose()
        self.publish_func = Mock()

    @patch("ryutils.firebase.collections.base.firebase_admin._apps", [])
    @patch("ryutils.firebase.collections.base.firebase_admin.initialize_app")
    @patch("ryutils.firebase.collections.base.credentials.Certificate")
    @patch("ryutils.firebase.collections.base.firestore.client")
    def test_manager_initialization(
        self, mock_client: Mock, mock_cert: Mock, mock_init: Mock  # pylint: disable=unused-argument
    ) -> None:
        """Test FirebaseManager initialization."""
        mock_db = Mock()
        mock_collection_ref = Mock()
        mock_collection_ref.on_snapshot = Mock(return_value=None)
        mock_db.collection = Mock(return_value=mock_collection_ref)
        mock_client.return_value = mock_db

        collection = MockFirebaseCollection(
            credentials_file=Path("/tmp/test.json"),
            verbose=self.verbose,
            collections=["test_collection"],
            auto_init=False,
        )

        def get_cache() -> dict:
            return T.cast(dict, collection.get_cache("test_collection"))

        def convert_func(cache: dict) -> ConfigMessagePb:  # pylint: disable=unused-argument
            pb = ConfigMessagePb()
            # ConfigMessagePb has a config map field, not config_json
            # For testing, we'll just return an empty message
            return pb

        config = ManagerCollectionConfig(
            collection=collection,
            get_cache_func=get_cache,
            message_pb_type=ConfigMessagePb,
            convert_func=convert_func,
            channel=channels.CONFIG_CHANNEL,
        )

        manager = FirebaseManager(
            verbose=self.verbose,
            collection_configs=[config],
            publish_func=self.publish_func,
        )

        self.assertTrue(manager.is_active())
        self.assertEqual(len(manager.collection_configs), 1)

    @patch("ryutils.firebase.collections.base.firebase_admin._apps", [])
    @patch("ryutils.firebase.collections.base.firebase_admin.initialize_app")
    @patch("ryutils.firebase.collections.base.credentials.Certificate")
    @patch("ryutils.firebase.collections.base.firestore.client")
    def test_manager_is_active(
        self, mock_client: Mock, mock_cert: Mock, mock_init: Mock  # pylint: disable=unused-argument
    ) -> None:
        """Test manager is_active method."""
        mock_db = Mock()
        mock_collection_ref = Mock()
        mock_collection_ref.on_snapshot = Mock(return_value=None)
        mock_db.collection = Mock(return_value=mock_collection_ref)
        mock_client.return_value = mock_db

        # Empty manager
        manager = FirebaseManager(
            verbose=self.verbose,
            collection_configs=[],
            publish_func=self.publish_func,
        )
        self.assertFalse(manager.is_active())

        # Manager with collections
        collection = MockFirebaseCollection(
            credentials_file=Path("/tmp/test.json"),
            verbose=self.verbose,
            collections=["test_collection"],
            auto_init=False,
        )

        def get_cache() -> dict:
            return {}

        def convert_func(cache: dict) -> ConfigMessagePb:  # pylint: disable=unused-argument
            return ConfigMessagePb()

        config = ManagerCollectionConfig(
            collection=collection,
            get_cache_func=get_cache,
            message_pb_type=ConfigMessagePb,
            convert_func=convert_func,
            channel=channels.CONFIG_CHANNEL,
        )

        manager = FirebaseManager(
            verbose=self.verbose,
            collection_configs=[config],
            publish_func=self.publish_func,
        )
        self.assertTrue(manager.is_active())

    @patch("ryutils.firebase.collections.base.firebase_admin._apps", [])
    @patch("ryutils.firebase.collections.base.firebase_admin.initialize_app")
    @patch("ryutils.firebase.collections.base.credentials.Certificate")
    @patch("ryutils.firebase.collections.base.firestore.client")
    def test_manager_step(
        self,
        mock_client: Mock,
        mock_cert: Mock,  # pylint: disable=unused-argument
        mock_init: Mock,  # pylint: disable=unused-argument
    ) -> None:
        """Test manager step method."""
        mock_db = Mock()
        mock_collection_ref = Mock()
        mock_collection_ref.on_snapshot = Mock(return_value=None)
        mock_db.collection = Mock(return_value=mock_collection_ref)
        mock_client.return_value = mock_db

        collection = MockFirebaseCollection(
            credentials_file=Path("/tmp/test.json"),
            verbose=self.verbose,
            collections=["test_collection"],
            auto_init=False,
        )

        def get_cache() -> dict:
            return {"test": "data"}

        def convert_func(cache: dict) -> ConfigMessagePb:  # pylint: disable=unused-argument
            pb = ConfigMessagePb()
            # ConfigMessagePb has a config map field, not config_json
            # For testing, we'll just return an empty message
            return pb

        config = ManagerCollectionConfig(
            collection=collection,
            get_cache_func=get_cache,
            message_pb_type=ConfigMessagePb,
            convert_func=convert_func,
            channel=channels.CONFIG_CHANNEL,
        )

        manager = FirebaseManager(
            verbose=self.verbose,
            collection_configs=[config],
            publish_func=self.publish_func,
        )

        # Mock internal methods using patch.object to avoid mypy errors
        with (
            patch.object(manager, "_check_from_firebase", Mock()) as mock_from,
            patch.object(manager, "_check_to_firebase", Mock()) as mock_to,
            patch.object(manager, "_check_and_maybe_publish", Mock()) as mock_publish,
        ):

            # Call step
            manager.step()

            # Verify internal methods were called
            mock_from.assert_called_once()
            mock_to.assert_called_once()
            # Verify publish was called for each collection
            self.assertEqual(mock_publish.call_count, 1)


class TestChangesEnum(unittest.TestCase):
    """Test Changes enum."""

    def test_changes_enum_values(self) -> None:
        """Test Changes enum has correct values."""
        self.assertEqual(Changes.ADDED.value, 1)
        self.assertEqual(Changes.MODIFIED.value, 2)
        self.assertEqual(Changes.REMOVED.value, 3)

    def test_changes_enum_names(self) -> None:
        """Test Changes enum has correct names."""
        self.assertEqual(Changes.ADDED.name, "ADDED")
        self.assertEqual(Changes.MODIFIED.name, "MODIFIED")
        self.assertEqual(Changes.REMOVED.name, "REMOVED")


if __name__ == "__main__":
    unittest.main()
