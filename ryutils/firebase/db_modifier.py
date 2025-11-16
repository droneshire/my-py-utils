"""
Firebase database modifier class.

This module provides a generic class for modifying Firebase collections.
It can download, upload, and modify documents in any Firebase collection.
"""

import json
import os
import typing as T
from collections import OrderedDict

import deepdiff

from ryutils import log
from ryutils.firebase.collections.base import FirebaseCollection


def sort_dict(d: T.Any) -> T.Any:
    """
    Recursively sort a dictionary.

    Args:
        d: Dictionary or nested structure to sort

    Returns:
        Sorted dictionary or structure
    """
    if isinstance(d, dict):
        return OrderedDict(sorted((k, sort_dict(v)) for k, v in d.items()))
    if isinstance(d, list):
        return [sort_dict(i) for i in d]
    return d


class FirebaseDbModifier:
    """
    Generic class for modifying Firebase collections.

    This class provides methods to download, upload, and modify documents
    in Firebase collections.
    """

    def __init__(
        self,
        collection: FirebaseCollection,
        collection_name: str,
        get_cache_func: T.Callable[[], T.Dict[str, T.Any]],
        log_dir: str,
        validate_func: T.Optional[T.Callable[[T.Dict[str, T.Any]], None]] = None,
    ) -> None:
        """
        Initialize Firebase database modifier.

        Args:
            collection: Firebase collection instance
            collection_name: Name of the collection
            get_cache_func: Function to get collection cache
            log_dir: Directory for log files
            validate_func: Optional function to validate uploaded data
        """
        self.collection = collection
        self.collection_name = collection_name
        self.get_cache_func = get_cache_func
        self.log_dir = log_dir
        self.validate_func = validate_func

    def check_for_changes(
        self,
        doc_id: str,
        old_data: T.Dict[str, T.Any],
        new_data: T.Dict[str, T.Any],
        verbose: bool = False,
    ) -> None:
        """
        Check for changes between old and new data.

        Args:
            doc_id: Document ID
            old_data: Old document data
            new_data: New document data
            verbose: Whether to print verbose output
        """
        if not new_data:
            return

        if verbose:
            log.print_normal(f"Updated data: {json.dumps(new_data, indent=2)}")

        diff = deepdiff.DeepDiff(old_data, new_data, ignore_order=True)

        if diff:
            diff_json = diff.to_json()
            # hack b/c of https://github.com/seperman/deepdiff/issues/490
            diff_json_sorted = json.dumps(json.loads(diff_json), indent=4, sort_keys=True)
            log.print_warn(f"Diff for document {doc_id}:\n{diff_json_sorted}")
        else:
            log.print_ok(f"No changes for document {doc_id}")

    def download(
        self,
        download_file: T.Optional[str] = None,
        update_from_firestore: bool = True,
    ) -> str:
        """
        Download collection data to a file.

        Args:
            download_file: Optional path to download file. If None, uses default location.
            update_from_firestore: Whether to update from Firestore before downloading

        Returns:
            Path to the downloaded file
        """
        if download_file is None:
            download_file = os.path.join(self.log_dir, f"firebase_{self.collection_name}_data.json")

        log.print_bright(
            f"Downloading Firebase collection `{self.collection_name}` data to {download_file}..."
        )

        if update_from_firestore:
            self.collection.update_from_firestore(self.collection_name)

        ordered_data = sort_dict(self.get_cache_func())

        with open(download_file, "w", encoding="utf-8") as outfile:
            json.dump(ordered_data, outfile, indent=2)
        log.print_ok_arrow(f"Download complete --> {download_file}")

        return download_file

    def upload(
        self,
        upload_file: T.Optional[str] = None,
        update_from_firestore: bool = True,
        update_firebase: bool = False,
        document_id: T.Optional[str] = None,
        ignore_missing_documents: bool = False,
    ) -> None:
        """
        Upload collection data from a file.

        Args:
            upload_file: Optional path to upload file. If None, uses default location.
            update_from_firestore: Whether to update from Firestore before uploading
            update_firebase: Whether to actually update Firebase (dry-run if False)
            document_id: Optional specific document ID to update (default: all documents)
            ignore_missing_documents: Whether to ignore missing documents when uploading
        """
        if upload_file is None:
            upload_file = os.path.join(self.log_dir, f"firebase_{self.collection_name}_data.json")

        log.print_bright(
            f"Uploading Firebase collection `{self.collection_name}` data from {upload_file}..."
        )
        with open(upload_file, "r", encoding="utf-8") as infile:
            updated_data = json.load(infile)

        old_data: T.Dict[str, T.Any] = {}
        try:
            if self.validate_func:
                self.validate_func(updated_data)
            if update_from_firestore:
                self.collection.update_from_firestore(self.collection_name)
            old_data = self.get_cache_func()
        except Exception as e:  # pylint: disable=broad-except
            log.print_fail(f"\n\nProposed upload data is invalid: {e}")
            return

        upload_data = dict(updated_data)

        for doc_id in upload_data:
            if doc_id not in old_data and not ignore_missing_documents:
                log.print_fail(
                    f"Document {doc_id} not found in Firebase data. "
                    "Use ignore_missing_documents=True to add anyways."
                )
                continue

            # Filter by document-id if specified
            if document_id and doc_id != document_id:
                continue

            self.check_for_changes(
                doc_id=doc_id,
                old_data=old_data.get(doc_id, {}),
                new_data=upload_data[doc_id],
                verbose=False,
            )

            if not update_firebase:
                continue

            self.collection.check_and_maybe_update_to_firestore(
                collection_name=self.collection_name,
                doc_id=doc_id,
                doc_data=upload_data[doc_id],
                ignore_missing=ignore_missing_documents,
            )
