"""
0G Storage Integration Module.

Provides upload/download functions for storing healthcare reconciliation
audit trails on the 0G decentralized storage network.

Uses python-0g (a0g) package for native Python integration.

Environment variables:
    ZG_PRIVATE_KEY:  Ethereum private key for signing storage transactions
    ZG_NETWORK:      0G network (testnet/mainnet, default: testnet)
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default 0G network
DEFAULT_NETWORK = "testnet"


class ZeroGStorageError(Exception):
    """Raised when 0G Storage operations fail."""
    pass


def _is_0g_available() -> bool:
    """Check if the python-0g (a0g) package is installed."""
    try:
        from a0g import A0G
        return True
    except ImportError:
        return False


def _get_config() -> dict[str, str]:
    """Read 0G configuration from environment variables."""
    return {
        "private_key": os.environ.get("ZG_PRIVATE_KEY", ""),
        "network": os.environ.get("ZG_NETWORK", DEFAULT_NETWORK),
    }


def upload_to_0g(data: dict, filename: str) -> str:
    """
    Upload data to 0G decentralized storage.

    Serializes the Python dict to JSON, writes to a temp file, then uploads
    via the python-0g (a0g) package.

    Args:
        data: Dictionary to upload (will be JSON-serialized)
        filename: Logical filename for the upload (used in metadata)

    Returns:
        Merkle root hash string identifying the uploaded data on 0G

    Raises:
        ZeroGStorageError: If upload fails
    """
    # Graceful degradation: if package not installed, return mock hash
    if not _is_0g_available():
        mock_hash = _generate_mock_hash(data, filename)
        logger.warning(
            "python-0g (a0g) not installed. "
            "Returning mock hash: %s. "
            "Install with: pip install python-0g>=0.6.1",
            mock_hash,
        )
        return mock_hash

    config = _get_config()
    if not config["private_key"]:
        mock_hash = _generate_mock_hash(data, filename)
        logger.warning(
            "ZG_PRIVATE_KEY not set. Returning mock hash: %s. "
            "Set ZG_PRIVATE_KEY environment variable for real uploads.",
            mock_hash,
        )
        return mock_hash

    # Write data to temp file
    tmp_dir = tempfile.mkdtemp(prefix="healthpay_0g_")
    tmp_path = Path(tmp_dir) / filename

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        # Upload via A0G
        from a0g import A0G
        client = A0G(
            private_key=config["private_key"],
            network=config["network"],
        )
        result = client.upload_to_storage(tmp_path)
        root_hash = result.root_hash

        logger.info(
            "Uploaded %s to 0G Storage. Root hash: %s, Tx hash: %s",
            filename, root_hash, result.tx_hash,
        )
        return root_hash

    except Exception as e:
        raise ZeroGStorageError(f"0G Storage upload failed: {e}")

    finally:
        # Clean up temp file
        try:
            tmp_path.unlink()
            Path(tmp_dir).rmdir()
        except OSError:
            pass


def download_from_0g(root_hash: str, output_path: str) -> dict:
    """
    Download data from 0G decentralized storage by Merkle root hash.

    Args:
        root_hash: Merkle root hash of the stored data
        output_path: Local file path to save the downloaded data

    Returns:
        Parsed JSON data as a Python dict

    Raises:
        ZeroGStorageError: If download fails
    """
    # Graceful degradation
    if not _is_0g_available():
        logger.warning(
            "python-0g (a0g) not installed. Cannot download hash %s. "
            "Install with: pip install python-0g>=0.6.1",
            root_hash,
        )
        return _generate_mock_download(root_hash)

    config = _get_config()
    if not config["private_key"]:
        logger.warning(
            "ZG_PRIVATE_KEY not set. Returning mock data for hash %s.",
            root_hash,
        )
        return _generate_mock_download(root_hash)

    try:
        from a0g import A0G
        from a0g.types.storage import ZGStorageObject

        client = A0G(
            private_key=config["private_key"],
            network=config["network"],
        )

        # Create storage object from root hash
        storage_obj = ZGStorageObject(root_hash=root_hash, tx_hash="")

        # Download
        output_path_obj = Path(output_path)
        client.download_from_storage(storage_obj, output_path_obj)

        # Read and parse the downloaded file
        with open(output_path_obj, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        raise ZeroGStorageError(f"0G Storage download failed: {e}")


def _generate_mock_hash(data: dict, filename: str) -> str:
    """
    Generate a deterministic mock Merkle root hash for testing/degraded mode.

    The hash is prefixed with '0xMOCK_' to make it obvious it's not real.
    """
    import hashlib
    content = json.dumps(data, sort_keys=True, default=str)
    digest = hashlib.sha256(content.encode()).hexdigest()
    return f"0xMOCK_{digest[:56]}"


def _generate_mock_download(root_hash: str) -> dict:
    """Generate mock download data for testing/degraded mode."""
    return {
        "mock": True,
        "root_hash": root_hash,
        "message": "python-0g not available — this is mock data",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
