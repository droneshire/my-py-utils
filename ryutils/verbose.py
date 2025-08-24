import argparse
import typing as T

from ryutils import log


class Verbose:
    DEFAULT_TYPES = [
        "general",
        "requests",
        "requests_url",
        "requests_response",
        "request_cache",
        "mitmproxy",
    ]
    # Add types here
    TYPES = []

    def __init__(
        self, args: T.Optional[argparse.Namespace] = None, print_args: bool = False
    ) -> None:
        for verbose_type in self.DEFAULT_TYPES + self.TYPES:
            setattr(self, verbose_type, False)

        if args is not None:
            for verbose_type in self.DEFAULT_TYPES + self.TYPES:
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
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        verbose_group = parser.add_argument_group("Verbose Options")
        verbose_group.add_argument("--verbose", action="store_true", help="Enable verbose mode")
        for verbose_type in Verbose.DEFAULT_TYPES + Verbose.TYPES:
            verbose_group.add_argument(
                f"--{verbose_type}-verbose",
                action="store_true",
                help=f"Enable verbose mode for {verbose_type}",
            )

    def __getattr__(self, name: str) -> T.Any:
        if name in self.DEFAULT_TYPES + self.TYPES:
            return False
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _string_repr(self) -> str:
        string_repr = ", ".join(
            [
                f"{verbose_type}={getattr(self, verbose_type)}"
                for verbose_type in self.DEFAULT_TYPES + self.TYPES
            ]
        )
        return string_repr

    def __repr__(self) -> str:
        string_repr = self._string_repr()
        return f"Verbose({string_repr})"
