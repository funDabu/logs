import re

from typing import List, Callable, TextIO, Iterator

from constants import LOG_ENTRY_REGEX
RE_PROG_ENTRY = re.compile(LOG_ENTRY_REGEX)


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


def parse_log_entry(entry: str) -> Log_entry:
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


def general_parse_entry_with_regex(line: str, re_prog) -> Log_entry:
    result = Log_entry()
    match = re_prog.search(line)

    if match is None:
        return result
    
    result.length = match.lastindex
    for i in range(match.lastindex):
        setattr(result, result.__slots__[i], match.group(i+1))
    
    return result


def parse_entry_with_regex(line: str) -> Log_entry:
    return general_parse_entry_with_regex(line, RE_PROG_ENTRY)


def regex_parser(input: TextIO, 
                 buffer_size: int = 1000,
                 parse_with_re: bool = True) -> Iterator[Log_entry]:
        
    buffer = []
    i = 0
    parse_func: Callable[[str], Log_entry] =\
        parse_entry_with_regex if parse_with_re else parse_log_entry

    for line in input:
        buffer.append(line)
        i += 1
        if i == buffer_size:
            yield map(parse_func, buffer)
            buffer = []
            i = 0
        
    if i > 0:
        yield map(parse_func, buffer)


#######################
##       TESTS       ##
#######################
        
def main():
    test_re_parse()
    # test_my_parse()
    # test_compare()


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
    test_parse(lambda line: parse_entry_with_regex(line))

def test_compare():
    import time
    import sys 

    # Python 3.7 and newer
    # https://stackoverflow.com/questions/16549332/python-3-how-to-specify-stdin-encoding
    # sys.stdin.reconfigure(encoding='utf-8')

    i = 1
    time1 = time.time()
    re_prog_entry = re.compile(LOG_ENTRY_REGEX)
    re_parse = lambda line: parse_entry_with_regex(line, re_prog_entry)

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
    main()