import os
import traceback


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
