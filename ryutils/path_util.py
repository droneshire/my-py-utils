import os
import traceback
from pathlib import Path

LOGS_DIR_NAME = "logs"
CONFIG_DIR_NAME = "config"
DATA_DIR_NAME = "data"
NOTEBOOKS_DIR_NAME = "notebooks"


def get_root_dir() -> Path:
    this_dir = os.path.dirname(os.path.realpath(__file__))
    src_dir = os.path.dirname(this_dir)
    root_dir = os.path.dirname(src_dir)
    return Path(root_dir)


def get_logging_dir(name: str, create_if_not_exist: bool = True) -> Path:
    root_dir = get_root_dir()
    log_dir = os.path.join(root_dir, LOGS_DIR_NAME, name)

    if create_if_not_exist:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    return Path(log_dir)


def get_config_dir() -> Path:
    """Get the config directory."""
    root_dir = get_root_dir()
    return Path(os.path.join(root_dir, CONFIG_DIR_NAME))


def get_data_dir() -> Path:
    """Get the data directory."""
    root_dir = get_root_dir()
    return Path(os.path.join(root_dir, NOTEBOOKS_DIR_NAME, DATA_DIR_NAME))


def get_module_name(file_path: str, layers: int = 1) -> str:
    """
    Get the module name from a file path from an executable path.

    Default assumes:

    ├── module_name
    │   ├── executables
    │   ├── __init__.py
    │   ├── called_from_here.py

    Args:
    - file_path (str): The file path to get the module name from.
    - layers (int): The number of layers to go up from the file path.

    Returns:
    - str: The module name.
    """
    this_dir = os.path.dirname(file_path)
    for _ in range(layers):
        this_dir = os.path.dirname(this_dir)
    return os.path.basename(this_dir)


def get_backtrace_file_name(frame: int = 1) -> str:
    """
    Get the file name from the backtrace.
    """
    tracing = traceback.extract_stack()
    frame_inx = len(tracing) - frame - 1
    assert frame_inx >= 0, f"Frame index {frame} is out of range"
    return os.path.basename(tracing[frame_inx].filename)
