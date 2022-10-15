from typing import List, Optional
import re

import sys


def parse_log_entry(entry: str, log_entry: Optional["Log_entry"] = None):
    end = None
    skip = False
    growing = []
    result = log_entry if log_entry else Log_entry()
    i = 0

    for ch in entry:
        if i > 8:
            # entry should be now parsed
            break
        elif skip:
            skip = False
        elif ch == '\\':
            skip = True
        elif end and ch == end:
            end = None
            setattr(result, result.__slots__[i], ''.join(growing))
            i += 1
            growing = []
        elif end:
            growing.append(ch)
        elif ch == ' ':
            if growing:
                setattr(result,
                        result.__slots__[i],
                        ''.join(growing))
                i += 1
            growing = []
        elif ch in '"[':
            end = ']' if ch == '[' else '"'
        else:
            growing.append(ch)

    result.length = i
    return result


class Log_entry:
    __slots__ = ("ip_addr", "slot1", "slot2", "time", "request",
                  "http_code", "bytes", "referer", "user_agent",
                  "length")

    def __init__(self):
        self.length = 0

    def __str__(self) -> str:
        content = [getattr(self, self.__slots__[i])\
                   for i in range(self.length)]
        content = ', '.join(content)
        return f'[{content}]'
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __len__(self):
        return self.length
    
    def get_bot_url(self) -> str:
        # if "user agent" field of the log entry doesn't contain
        # bot's url, return empty string
        match = re.search(r"(http\S+?)[);]", self.user_agent)
        if match is None:
            return ""
        return match.group(1)


def main():
    
    import time
    import sys 

    counter = 1
    time1 = time.time()
    print("Test has just started", file=sys.stderr)

    for line in sys.stdin:
        entry = parse_log_entry(line)
        if entry.length < 9:
            print(f"Error no.{counter}", file=sys.stderr)
            counter += 1
            print("Original log entry:", line, file=sys.stderr)
            print("Parsed entry:", entry, file=sys.stderr)
            print("", file=sys.stderr)

    print(f"Test has ended, took {round(time.time() - time1, 1)} sec", file=sys.stderr)  


if __name__ == "__main__":
    main()