import os
import unittest
from unittest import mock

from stremio_private.cli import _watch_parent


class RecordingServer:
    def __init__(self):
        self.shutdown_calls = 0

    def shutdown(self):
        self.shutdown_calls += 1


class ParentWatchTests(unittest.TestCase):
    def test_stops_server_when_desktop_parent_is_gone(self):
        server = RecordingServer()
        with mock.patch.object(os, "getppid", return_value=999):
            _watch_parent(server, parent_pid=123, poll_interval=0)
        self.assertEqual(server.shutdown_calls, 1)


if __name__ == "__main__":
    unittest.main()
