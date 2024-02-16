import re

from typing import  TextIO, Iterator

from logs.helpers.constants import LOG_ENTRY_REGEX
from logs.parser.logentry import Log_entry

RE_PROG_ENTRY = re.compile(LOG_ENTRY_REGEX)


def general_parse_entry_with_regex(line: str, re_prog) -> Log_entry:
    # re_prog is compiled re.Pattern object

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
                 buffer_size: int = 1000)\
        -> Iterator[Log_entry]:
    """Reads `buffer_size` lines from `input`,
    parses them with regex and yields an iterator
    `buffer_size` Log_entries"""
        
    buffer = []
    i = 0

    for line in input:
        buffer.append(line)
        i += 1
        if i == buffer_size:
            yield map(parse_entry_with_regex, buffer)
            buffer = []
            i = 0
        
    if i > 0:
        yield map(parse_entry_with_regex, buffer)
