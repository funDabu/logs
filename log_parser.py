from ast import Call
from typing import List, Optional, Callable
import re
from unittest import TestSuite


LOG_ENTRY_REGEX = r'^([0-9.]+?) (.+?) (.+?) \[(.+?)\] "(.*?[^\\])" ([0-9]+?) ([0-9\-]+?) "(.*?[^\\])" "(.*?[^\\])"'
BOT_URL_REGEX = r"(http\S+?)[);]"


def parse_log_entry(entry: str) -> "Log_entry":
    end = None
    skip = False
    growing = []
    result = Log_entry()
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
        match = re.search(BOT_URL_REGEX, self.user_agent)
        if match is None:
            return ""
        return match.group(1)


def parse_with_regex(line: str, re_prog: re.Pattern) -> Log_entry:
    result = Log_entry()
    match = re_prog.search(line)

    if match is None:
        return result
    
    result.length = match.lastindex
    for i in range(match.lastindex):
        setattr(result, result.__slots__[i], match.group(i+1))
    
    return result


class Log_parser:
    def __init__(self):
        self.re_prog_entry = re.compile(LOG_ENTRY_REGEX)
        self.re_prog_bot_url = re.compile(BOT_URL_REGEX)

    def parse_with_regex(self, line:str):
        return parse_with_regex(line, self.re_prog_entry)

    #TODO: add is_bot method

    def parse(self,
              input_path:str, 
              buffer_size: int = 1000,
              parse_with_re: bool = False):
        
        buffer = []
        i = 0
        parse_func: Callable[[str], Log_entry] =\
            self.parse_with_regex if parse_with_re else parse_log_entry

        with open(input_path, "r") as f:
            for line in f:
                buffer.append(parse_func(line))
                i += 1
                if i == buffer_size:
                    yield buffer
                    buffer = []
                    i = 0
            
        if i > 0:
            yield buffer


#######################
##       TESTS       ##
#######################
        
def main():
    test_re_parse()
    # test_my_parse()


def check_entry_length(entry: Log_entry, line: str, counter:int, output):
    if entry.length < 9:
        
        print(f"Error no.{counter}", file=output)
        counter += 1
        print("Original log entry:", line, file=output)
        print("Parsed entry:", entry, file=output)
        print("", file=output)

def test_parse(func: Callable[[str], Log_entry]):
    import time
    import sys 

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
    re_prog_entry = re.compile(LOG_ENTRY_REGEX)
    test_parse(lambda line: parse_with_regex(line, re_prog_entry))
      

if __name__ == "__main__":
    main()