import re
from typing import Callable

from logs.parser.log_parser import (
    LOG_ENTRY_REGEX,
    Log_entry,
    parse_entry_with_regex,
    parse_log_entry,
)


def run_test():
    test_re_parse()
    # test_my_parse()
    # test_compare()


def check_entry_length(entry: Log_entry, line: str, counter: int, output):
    if entry.length < 9:
        print(f"Error no.{counter}", file=output)
        counter += 1
        print("Original log entry:", line, file=output)
        print("Parsed entry:", entry, file=output)
        print("", file=output)


def test_parse(func: Callable[[str], Log_entry]):
    import sys
    import time

    i = 1
    time1 = time.time()
    print("Test has started", file=sys.stderr)

    for line in sys.stdin:
        entry = func(line)
        check_entry_length(entry, line, i, sys.stderr)
        i += 1

    print(f"Test has ended, took {round(time.time() - time1, 1)} sec", file=sys.stderr)


def test_my_parse():
    test_parse(parse_log_entry)


def test_re_parse():
    test_parse(lambda line: parse_entry_with_regex(line))


def test_compare():
    import sys
    import time

    i = 1
    time1 = time.time()
    re_prog_entry = re.compile(LOG_ENTRY_REGEX)

    def re_parse(line):
        return parse_entry_with_regex(line, re_prog_entry)

    print("Test has started", file=sys.stderr)

    for line in sys.stdin:
        mine = parse_log_entry(line)
        re_parsed = re_parse(line)

        mine_s = mine.__str__()
        re_parsed_s = re_parsed.__str__()

        if mine_s != re_parsed_s:
            print(f"error line no.{i}", file=sys.stderr)
            print("mine:", file=sys.stderr)
            print(mine_s, file=sys.stderr)
            print("regex:", file=sys.stderr)
            print(re_parsed_s, "\n", file=sys.stderr)

        i += 1

    print(f"Test has ended, took {round(time.time() - time1, 1)} sec", file=sys.stderr)


if __name__ == "__main__":
    run_test()
