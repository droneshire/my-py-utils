import argparse
import typing as T

from ryutils import log


class Verbose:
    DEFAULT_TYPES: T.List[str] = [
        "general",
        "requests",
        "requests_url",
        "requests_response",
        "request_cache",
        "mitmproxy",
        "firebase",
    ]
    TYPES: T.List[str] = []

    def __init__(
        self,
        args: T.Optional[argparse.Namespace] = None,
        print_args: bool = False,
        verbose_types: T.Optional[T.List[str]] = None,
    ) -> None:
        self.TYPES = Verbose.DEFAULT_TYPES.copy()  # pylint: disable=invalid-name

        if verbose_types is not None:
            self.TYPES.extend(verbose_types)

        for verbose_type in self.TYPES:
            setattr(self, verbose_type, False)

        if args is not None:
            for verbose_type in self.TYPES:
                setattr(
                    self,
                    verbose_type,
                    getattr(args, f"{verbose_type}_verbose", False) or args.verbose,
                )
        if print_args:
            self.print_verbose_args()

    def print_verbose_args(self) -> None:
        print_str = "\n\t".join(str(self._string_repr()).split(", "))
        log.print_normal(f"Verbose args:\n\t{print_str}")

    @staticmethod
    def add_arguments(
        parser: argparse.ArgumentParser,
        verbose_types: T.Optional[T.List[str]] = None,
    ) -> None:
        verbose_group = parser.add_argument_group(
            "Verbose Options", description="Control verbosity levels for different components"
        )
        verbose_group.add_argument("--verbose", action="store_true", help="Enable verbose mode")

        all_verbose_types = Verbose.DEFAULT_TYPES.copy()
        if verbose_types is not None:
            all_verbose_types.extend(verbose_types)

        for verbose_type in all_verbose_types:
            verbose_group.add_argument(
                f"--{verbose_type}-verbose",
                action="store_true",
                help=f"Enable verbose mode for {verbose_type}",
            )

    def __getattr__(self, name: str) -> T.Any:
        if name in self.TYPES:
            return False
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _string_repr(self) -> str:
        string_repr = ", ".join(
            [f"{verbose_type}={getattr(self, verbose_type)}" for verbose_type in self.TYPES]
        )
        return string_repr

    def __repr__(self) -> str:
        string_repr = self._string_repr()
        return f"Verbose({string_repr})"
