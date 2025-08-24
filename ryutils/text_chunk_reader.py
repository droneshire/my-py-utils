import typing as T
from pathlib import Path


class TextChunkReader:
    def __init__(self, path: T.Union[Path, str], chunk_size: int = 1024) -> None:
        self.path = path

        self.file: T.Optional[T.TextIO] = None
        try:
            self.file = open(path, "r", encoding="utf-8")  # pylint: disable=consider-using-with
        except FileNotFoundError:
            pass

        self.chunk_size = chunk_size
        self.buffer = ""  # Buffer to hold incomplete words
        self.write_buffer = ""

    def __iter__(self) -> T.Generator[str, None, None]:
        if self.file is None:
            return

        while True:
            chunk = self.buffer + self.file.read(self.chunk_size)
            if not chunk:
                break

            chunk_ends_in_punctuation_or_space = chunk[-1] in ".,;:"
            last_indicator_index = max(chunk.rfind(" "), chunk.rfind("\n"), chunk.rfind("\t"))
            if last_indicator_index == -1 or chunk_ends_in_punctuation_or_space:
                self.buffer = ""
                yield chunk
            else:
                last_indicator = chunk[last_indicator_index]
                self.buffer = chunk[last_indicator_index + 1 :]
                yield chunk[:last_indicator_index] + last_indicator

    def close(self) -> None:
        if self.file is None:
            return

        # Write any remaining buffer to the file if we're closing
        if self.write_buffer:
            with open(self.path, "a", encoding="utf-8") as outfile:
                outfile.write(self.write_buffer)

        self.file.close()

    def write(self, data: str) -> None:
        self.write_buffer += data

        if len(self.write_buffer) <= self.chunk_size:
            return

        with open(self.path, "a", encoding="utf-8") as outfile:
            outfile.write(self.write_buffer)

        self.write_buffer = ""
