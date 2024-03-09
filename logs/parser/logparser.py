import re
from typing import Callable, Iterator, TextIO

from logs.parser.logentry import LogEntry

# LOG_ENTRY_REGEX = r'([0-9.]+?) (.+?) (.+?) \[(.+?)\] "(.*?[^\\])" ([0-9]+?) ([0-9\-]+?) "(.*?)(?<!\\)" "(.*?)(?<!\\)"'
# matches only numbers and dots in the first - 'Host' group - eg. excepts only IPv4 as a host
LOG_ENTRY_REGEX = r'(\S+) (.+?) (.+?) \[(.+?)\] "(.*?[^\\])" ([0-9]+?) ([0-9\-]+?) "(.*?)(?<!\\)" "(.*?)(?<!\\)"'
# matches all nonwhitespace characters in the first - 'Host' group - e.g allows for both IP address and hostname as a host


def get_log_entry_parser(re_prog) -> Callable[[str], LogEntry]:
    """`re_prog` is compiled re.Pattern object of log entry regex"""

    def log_entry_parser(line: str) -> LogEntry:
        result = LogEntry()
        match = re_prog.search(line)

        if match is None:
            return result

        result.length = match.lastindex
        for i in range(match.lastindex):
            setattr(result, result.__slots__[i], match.group(i + 1))

        return result

    return log_entry_parser


def regex_parser(input: TextIO, buffer_size: int = 1000) -> Iterator[LogEntry]:
    """Reads `buffer_size` lines from `input`,
    parses them with regex and yields an iterator of
    `buffer_size` of Log_entries
    """

    re_prog_entry = re.compile(LOG_ENTRY_REGEX)
    buffer = []
    i = 0

    for line in input:
        buffer.append(line)
        i += 1
        if i == buffer_size:
            yield map(get_log_entry_parser(re_prog_entry), buffer)
            buffer = []
            i = 0

    if i > 0:
        yield map(get_log_entry_parser(re_prog_entry), buffer)
