import enum
import logging
import os
import shutil
import sys
import tarfile
import time
import typing as T
from pathlib import Path

_DEFAULT_DOWNSAMPLE_COUNT = 20
_ALWAYS_PRINT = False
_DOWNSAMPLER: T.Dict[str, T.Dict[str, int]] = {}
_DOWNSAMPLE_COUNT = _DEFAULT_DOWNSAMPLE_COUNT
_CALLBACK: T.Optional[T.Callable[[str], None]] = None
_CALLBACK_LEVEL = logging.WARNING


class Colors(enum.Enum):
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[31m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Prefixes(enum.Enum):
    ARROW = chr(10236)


class MultiHandler(logging.Handler):
    """
    Create a special logger that logs to per-thread-name files
    I'm not confident the locking strategy here is correct, I think this is
    a global lock and it'd be OK to just have a per-thread or per-file lock.
    """

    def __init__(self, dirname: str, block_list_prefixes: T.Optional[T.List[str]] = None):
        super().__init__()
        self.files: T.Dict[str, T.TextIO] = {}
        self.dirname = dirname
        self.block_list_prefixes = block_list_prefixes if block_list_prefixes else []
        if not os.access(dirname, os.W_OK):
            raise OSError(f"Directory {dirname} not writeable")

    def flush(self) -> None:
        self.acquire()
        try:
            for file_descriptor in self.files.values():
                file_descriptor.flush()
        finally:
            self.release()

    def close(self) -> None:
        """Close all open file handles."""
        self.acquire()
        try:
            for file_descriptor in self.files.values():
                file_descriptor.close()
            self.files.clear()
        finally:
            self.release()
        super().close()

    def _get_or_open(self, key: str) -> T.Optional[T.TextIO]:
        "Get the file pointer for the given key, or else open the file"
        self.acquire()
        try:
            if key in self.files:
                return self.files[key]

            file_name = (
                f"{key}.log".replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "")
            )
            file_name = file_name.lower()
            file_descriptor = open(  # pylint: disable=consider-using-with
                os.path.join(self.dirname, file_name),
                "a",
                encoding="utf-8",
            )
            self.files[key] = file_descriptor
            return file_descriptor
        finally:
            self.release()

    def emit(self, record: logging.LogRecord) -> None:
        # No lock here; following code for StreamHandler and FileHandler
        try:
            name = record.threadName
            if name is None:
                return
            if any(name.startswith(prefix) for prefix in self.block_list_prefixes):
                return
            file_descriptor = self._get_or_open(name)
            if file_descriptor is None:
                raise ValueError(f"Could not open file for {name}")
            msg = self.format(record)
            file_descriptor.write(f"{msg}\n")
        except (KeyboardInterrupt, SystemExit):
            raise
        except:  # pylint: disable=bare-except
            self.handleError(record)


def clean_log_dir(log_dir: str) -> None:
    """Clean the log directory by removing all files and directories in the directory."""
    if not os.path.exists(log_dir):
        return
    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as exception_obj:  # pylint: disable=broad-except
            print(f"Failed to delete {file_path}. Reason: {exception_obj}")


def is_color_supported() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def get_log_dir_name(log_dir: str) -> str:
    current_log_dir_name = time.strftime("%Y_%m_%d__%H_%M_%S", time.localtime(time.time()))
    updated_log_dir = os.path.join(log_dir, "logs", current_log_dir_name)
    Path(updated_log_dir).mkdir(parents=True, exist_ok=True)
    return updated_log_dir


def update_callback(
    callback: T.Optional[T.Callable[[str], None]], callback_level: int = logging.WARNING
) -> None:
    global _CALLBACK  # pylint: disable=global-statement
    global _CALLBACK_LEVEL  # pylint: disable=global-statement
    _CALLBACK = callback
    _CALLBACK_LEVEL = callback_level


def setup(
    log_dir: str,
    log_level: str,
    main_thread_name: str,
    always_print: bool = False,
    downsample_count: int = 1,
    use_multihandler: bool = True,
    callback: T.Optional[T.Callable[[str], None]] = None,
    callback_level: int = logging.WARNING,
) -> None:
    global _ALWAYS_PRINT  # pylint: disable=global-statement
    global _DOWNSAMPLE_COUNT  # pylint: disable=global-statement
    global _CALLBACK  # pylint: disable=global-statement
    global _CALLBACK_LEVEL  # pylint: disable=global-statement
    _ALWAYS_PRINT = always_print
    _DOWNSAMPLE_COUNT = downsample_count
    _CALLBACK = callback
    _CALLBACK_LEVEL = callback_level

    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)

    new_log_dir = get_log_dir_name(log_dir)

    setup_log(
        log_level,
        new_log_dir,
        main_thread_name,
    )

    if not use_multihandler:
        return

    logging.getLogger().addHandler(
        MultiHandler(
            new_log_dir,
            ["ThreadPool", "MainThread"],
        )
    )


def get_downsample_count() -> int:
    return _DOWNSAMPLE_COUNT


def make_formatter_printer(
    color: str,
    log_level: int = logging.INFO,
    prefix: str = "",
    return_formatter: bool = False,
    downsample: bool = False,
) -> T.Callable:
    logger = logging.getLogger(__name__)

    def formatter(message: T.Any, *args: T.Any, **kwargs: T.Any) -> str:
        message = str(message)

        if args or kwargs:
            formatted_text = message.format(*args, **kwargs)
        else:
            formatted_text = message

        if prefix and sys.platform.lower() == "linux":
            formatted_text = prefix + "\t" + formatted_text

        if is_color_supported():
            if sys.stdout.encoding is not None:
                return (
                    str(color + formatted_text + Colors.ENDC.value)
                    .encode("utf-8")
                    .decode(sys.stdout.encoding, errors="ignore")
                )
            return str(color + formatted_text + Colors.ENDC.value)

        if sys.stdout.encoding is not None:
            return T.cast(
                str, formatted_text.encode("utf-8").decode(sys.stdout.encoding, errors="ignore")
            )

        return T.cast(str, formatted_text)

    def printer(message: T.Any, *args: T.Any, **kwargs: T.Any) -> None:
        is_logger_in_use = logging.getLogger().hasHandlers()

        downsample_val = get_downsample_count() if downsample else 1

        formatted_text = formatter(message, *args, **kwargs)

        # obtain the backtrace of the caller to use as the key
        frame = sys._getframe(1)  # pylint: disable=protected-access
        key = frame.f_code.co_filename + frame.f_code.co_name + str(frame.f_lineno) + formatted_text

        should_print = False
        if downsample_val > 1:
            if key not in _DOWNSAMPLER:
                # set the count to downsample_val - 1 so that the first message is always printed
                _DOWNSAMPLER[key] = {"downsample": downsample_val, "count": downsample_val - 1}

            # Increment the count
            _DOWNSAMPLER[key]["count"] += 1

            # Check if we should print based on downsampling
            if _DOWNSAMPLER[key]["count"] % _DOWNSAMPLER[key]["downsample"] == 0:
                should_print = True
        else:
            should_print = True

        # Print if always_print, should_print, or logger not in use or enabled
        if (
            _ALWAYS_PRINT
            or should_print
            or (not is_logger_in_use or logging.getLogger().isEnabledFor(log_level))
        ):
            print(formatted_text)

        # Log to logger if in use
        if is_logger_in_use:
            log_methods = {
                logging.DEBUG: logger.debug,
                logging.WARNING: logger.warning,
                logging.ERROR: logger.error,
                logging.INFO: logger.info,
                logging.CRITICAL: logger.critical,
            }
            log_method = log_methods.get(log_level)
            if log_method:
                log_method(message)

        if _CALLBACK and log_level >= _CALLBACK_LEVEL:
            _CALLBACK(formatted_text)

        sys.stdout.flush()

    if return_formatter:
        return formatter

    return printer


def tar_logs(log_dir: str, tarname: str, remove_after: bool = False, max_tars: int = 5) -> None:
    """Tar the logs directory to a file called logs.tar.gz"""
    # Extract base name without extension
    if tarname.endswith(".tar.gz"):
        base_name = tarname[:-7]  # Remove .tar.gz
    else:
        base_name = tarname
        tarname = f"{base_name}.tar.gz"

    # if there are other tar names, increment the name by 1
    tar_index = 1
    original_tarname = tarname
    while os.path.exists(os.path.join(log_dir, tarname)):
        tarname = f"{base_name}.{tar_index}.tar.gz"
        tar_index += 1
        if tar_index > max_tars:
            # If we've exceeded max_tars, use the original name and overwrite
            tarname = original_tarname
            break

    logs_dir = os.path.join(log_dir, "logs")
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    tar_name = os.path.join(log_dir, tarname)
    with tarfile.open(tar_name, "w:gz") as tar:
        tar.add(logs_dir, arcname="logs")

    if remove_after:
        shutil.rmtree(logs_dir)


def setup_log(
    log_level: str,
    log_dir: str,
    id_string: str,
) -> None:

    if log_level == "NONE":
        return

    log_file = os.path.join(log_dir, f"{id_string}.log")

    log_level_num = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        filename=log_file,
        level=log_level_num,
        format="[%(levelname)s][%(asctime)s][%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filemode="w",
    )


print_ok_blue = make_formatter_printer(Colors.OKBLUE.value, log_level=logging.INFO)
print_ok_blue_arrow = make_formatter_printer(
    Colors.OKBLUE.value, prefix=Prefixes.ARROW.value, log_level=logging.INFO
)
print_ok = make_formatter_printer(Colors.OKGREEN.value, log_level=logging.ERROR)
print_ok_arrow = make_formatter_printer(
    Colors.OKGREEN.value, prefix=Prefixes.ARROW.value, log_level=logging.ERROR
)
print_bright = make_formatter_printer(Colors.OKCYAN.value, log_level=logging.WARNING)
print_warn = make_formatter_printer(Colors.WARNING.value, log_level=logging.WARNING)
print_fail = make_formatter_printer(Colors.FAIL.value, log_level=logging.CRITICAL)
print_fail_arrow = make_formatter_printer(
    Colors.FAIL.value, prefix=Prefixes.ARROW.value, log_level=logging.CRITICAL
)
print_bold = make_formatter_printer(Colors.BOLD.value, log_level=logging.ERROR)
print_normal = make_formatter_printer(Colors.ENDC.value, log_level=logging.DEBUG)
print_normal_arrow = make_formatter_printer(
    Colors.ENDC.value, prefix=Prefixes.ARROW.value, log_level=logging.DEBUG
)

print_ok_blue_slow = make_formatter_printer(
    Colors.OKBLUE.value, log_level=logging.INFO, downsample=True
)
print_ok_blue_arrow_slow = make_formatter_printer(
    Colors.OKBLUE.value,
    prefix=Prefixes.ARROW.value,
    log_level=logging.INFO,
    downsample=True,
)
print_ok_slow = make_formatter_printer(
    Colors.OKGREEN.value, log_level=logging.CRITICAL, downsample=True
)
print_ok_arrow_slow = make_formatter_printer(
    Colors.OKGREEN.value,
    prefix=Prefixes.ARROW.value,
    log_level=logging.CRITICAL,
    downsample=True,
)
print_bright_slow = make_formatter_printer(
    Colors.OKCYAN.value, log_level=logging.WARNING, downsample=True
)
print_warn_slow = make_formatter_printer(
    Colors.WARNING.value, log_level=logging.WARNING, downsample=True
)
print_fail_slow = make_formatter_printer(
    Colors.FAIL.value, log_level=logging.CRITICAL, downsample=True
)
print_fail_arrow_slow = make_formatter_printer(
    Colors.FAIL.value,
    prefix=Prefixes.ARROW.value,
    log_level=logging.CRITICAL,
    downsample=True,
)
print_bold_slow = make_formatter_printer(
    Colors.BOLD.value, log_level=logging.CRITICAL, downsample=True
)
print_normal_slow = make_formatter_printer(
    Colors.ENDC.value, log_level=logging.DEBUG, downsample=True
)
print_normal_arrow_slow = make_formatter_printer(
    Colors.ENDC.value,
    prefix=Prefixes.ARROW.value,
    log_level=logging.DEBUG,
    downsample=True,
)


format_ok_blue = make_formatter_printer(Colors.OKBLUE.value, return_formatter=True)
format_ok = make_formatter_printer(Colors.OKGREEN.value, return_formatter=True)
format_bright = make_formatter_printer(Colors.OKCYAN.value, return_formatter=True)
format_warn = make_formatter_printer(Colors.WARNING.value, return_formatter=True)
format_fail = make_formatter_printer(Colors.FAIL.value, return_formatter=True)
format_bold = make_formatter_printer(Colors.BOLD.value, return_formatter=True)
format_normal = make_formatter_printer(Colors.ENDC.value, return_formatter=True)
format_normal_arrow = make_formatter_printer(
    Colors.ENDC.value, prefix=Prefixes.ARROW.value, return_formatter=True
)
format_ok_arrow = make_formatter_printer(
    Colors.OKGREEN.value, prefix=Prefixes.ARROW.value, return_formatter=True
)
format_ok_blue_arrow = make_formatter_printer(
    Colors.OKBLUE.value, prefix=Prefixes.ARROW.value, return_formatter=True
)
format_fail_arrow = make_formatter_printer(
    Colors.FAIL.value, prefix=Prefixes.ARROW.value, return_formatter=True
)
