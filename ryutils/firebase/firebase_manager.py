import time
import typing as T

import deepdiff
from google.protobuf.message import Message  # pylint: disable=no-name-in-module

from ryutils.firebase.collections.base import FirebaseCollection
from ryutils.verbose import Verbose


class CollectionConfig(T.NamedTuple):
    """Configuration for a Firebase collection to manage."""

    collection: FirebaseCollection
    get_cache_func: T.Callable[[], T.Any]
    message_pb_type: T.Type[Message]
    convert_func: T.Callable[[T.Any], Message]
    channel: T.Any


class FirebaseManager:
    """
    Generic manager class for Firebase based configuration.

    This manager coordinates multiple Firebase collections and handles updates.
    Publishing/subscribing to Redis channels is handled by the caller via callbacks.

    Example usage:

        # Create your collection instances
        my_collection = MyFirebaseCollection(credentials_file, verbose)

        # Create manager with collection configurations
        manager = FirebaseManager(
            verbose=verbose,
            collection_configs=[
                CollectionConfig(
                    collection=my_collection,
                    get_cache_func=my_collection.get_cache,
                    message_pb_type=MyMessagePb,
                    convert_func=convert_my_data_to_pb,
                    channel=my_channel,  # Any channel type
                ),
            ],
            publish_func=lambda channel, message: redis_client.publish(  # noqa: ARG005
                channel, message
            ),
        )
    """

    TIME_BETWEEN_FIREBASE_QUERIES = 60 * 60 * 1  # 1 hour
    PUBLISH_FREQUENCY = 10.0

    def __init__(
        self,
        verbose: Verbose,
        collection_configs: T.List[CollectionConfig],
        publish_func: T.Callable[[T.Any, bytes], None],
        message_handlers: T.Optional[T.Dict[T.Any, T.Callable]] = None,
    ):
        """
        Initialize Firebase Manager.

        Args:
            verbose: Verbose configuration
            collection_configs: List of collection configurations to manage
            publish_func: Function to publish messages to Redis channels
            message_handlers: Optional dictionary of channel to message handler functions
        """
        self.verbose = verbose
        self.collection_configs = collection_configs
        self.publish_func = publish_func
        self.message_handlers = message_handlers or {}

        # Track last query time
        self.last_query_firebase_time: T.Optional[float] = None

        # Track last database state and publish times for each collection
        self.last_dbs: T.Dict[str, T.Any] = {}
        self.last_publish_time: T.Dict[str, float] = {}

        # Initialize tracking dictionaries
        for config in self.collection_configs:
            type_name = config.message_pb_type.__name__
            self.last_dbs[type_name] = {}
            self.last_publish_time[type_name] = 0.0

    def is_active(self) -> bool:
        """Check if manager is active (has collections configured)."""
        return len(self.collection_configs) > 0

    def init(self) -> None:
        """Initialize all collections."""
        for config in self.collection_configs:
            config.collection.init()

    def step(self) -> None:
        """Perform one step of the manager loop."""
        self._check_from_firebase()
        self._check_to_firebase()

        # Check and publish updates for each collection
        for config in self.collection_configs:
            new_db = config.get_cache_func()
            self._check_and_maybe_publish(
                new_db, config.message_pb_type, config.convert_func, config.channel
            )

    def _check_and_maybe_publish(
        self,
        new_db: T.Any,
        data_pb_type: T.Type[Message],
        convert_func: T.Callable[[T.Any], Message],
        channel: T.Any,
    ) -> None:
        """Check for changes and publish if needed."""
        diff = deepdiff.DeepDiff(self.last_dbs[data_pb_type.__name__], new_db, ignore_order=True)
        self.last_dbs[data_pb_type.__name__] = new_db

        now = time.time()

        if (
            not diff
            and now - self.last_publish_time[data_pb_type.__name__] < self.PUBLISH_FREQUENCY
        ):
            return

        self.last_publish_time[data_pb_type.__name__] = now

        message_pb: Message = convert_func(new_db)

        self.publish_func(channel, message_pb.SerializeToString())

    def _check_to_firebase(self) -> None:
        """Check and perform periodic updates to Firebase."""
        # Call collection-specific update methods
        # This allows collections to perform periodic tasks like health pings
        for config in self.collection_configs:
            config.collection.to_firebase()

    def _check_from_firebase(self) -> None:
        """Check and handle updates from Firebase."""
        # Update watchers periodically
        self._maybe_get_synchronous_update_from_firebase()

        # Let each collection handle its own updates
        for config in self.collection_configs:
            config.collection.check_and_maybe_handle_updates()

    def _maybe_get_synchronous_update_from_firebase(self) -> None:
        """Periodically refresh watchers from Firebase."""
        update_from_firebase = False
        if self.last_query_firebase_time is None:
            update_from_firebase = True
        else:
            time_since_last_update = time.time() - self.last_query_firebase_time
            update_from_firebase = time_since_last_update > self.TIME_BETWEEN_FIREBASE_QUERIES

        if update_from_firebase:
            self.last_query_firebase_time = time.time()
            # Update watchers for all collections
            for config in self.collection_configs:
                config.collection.update_watchers()
