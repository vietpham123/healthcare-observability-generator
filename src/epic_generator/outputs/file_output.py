import fcntl
import os


class FileOutput:
    """Write formatted log events to a file with locking."""

    def __init__(self, filename, append=False):
        self.filename = filename
        self.append = append
        self._first_write = True

    def write(self, formatted_event):
        """Write a single formatted event line to the file."""
        if self._first_write and not self.append:
            mode = "w"
            self._first_write = False
        else:
            mode = "a"
            self._first_write = False

        with open(self.filename, mode) as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(formatted_event)
            f.write("\n")
            fcntl.flock(f, fcntl.LOCK_UN)

    def close(self):
        """No-op for file output; included for interface consistency."""
        pass
