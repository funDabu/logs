import argparse
import os
import sys
import datetime as dt
import re


"""
========== TYPES ==========
"""

from typing import TextIO, Optional, List, Iterator, Iterable, Tuple, Dict, Callable

TimeInterval = Tuple[dt.datetime, dt.datetime]
CollisionJson = Tuple[Tuple[str, str], int, int]

"""
========== CONSTANTS ==========
"""

from constants import TIME_REGEX, DT_FORMAT, LOG_DT_FORMAT

RE_PROG_TIME = re.compile(TIME_REGEX)

DEF_FUSE_DELIM = 3600 # in seconds
DIR_PATH = "." # default output directory


"""
========== CLASSES ==========
"""

class Buffer:
    def __init__(self, lines: List[str] = []):
        self._lines: List[str] = lines
        self._head_i = 0
        self._end_i = len(lines) - 1

        self.__locked = False
        self.__i = 0

        self.first_time: Optional[dt.datetime] = None
        self.last_time: Optional[dt.datetime] = None

        if self.__len__() > 0:
            self.__set_first()
            self.__set_last()
    
    def __set_first(self) -> None:
        if  self._head_i >= self.__len__():
            self.first_time = None
            return

        self.first_time = get_time(self._lines[self._head_i])
    
    def __set_last(self) -> None:
        self.last_time = get_time(self._lines[self._end_i])
    
    def get_lines(self, start: int, end: int) -> List[str]:
        # result includes idices start and end
        end = self._end_i if end == -1 else\
              min(self._end_i, end + self._head_i)

        return self._lines[self._head_i + start : end + 1]
    
    def pop_left(self, n:int = 1) -> Optional[str]:
        if self.__locked or self.__len__() < n:
            return

        self._head_i += n
        self.__set_first()
        return self._lines[self._head_i - 1]
    
    def peek_left(self):
        if self.__len__() > 0:
            return self._lines[self._head_i]
    
    def __iter__(self) -> "Buffer":
        self.__locked = True
        self.__i = self._head_i

        return self
    
    def __next__(self) -> str:
        if self.__i <= self._end_i:
            self.__i += 1
            return self._lines[self.__i - 1]

        self.__locked = False
        raise StopIteration
    
    def stop_iter(self) -> None:
        self.__locked = False
        self.__i = self._end_i + 1

    def __len__(self) -> int:
        return self._end_i - self._head_i + 1

class Writer:
    def __init__(self, dir_path: str, log_name: str) -> None:
        self.__dir_path = os.path.realpath(dir_path)
        self.__log_name = log_name
        self._out_data: Dict[Tuple[int, int], List[Buffer]] = {}
    
    def append(self, buffer: Buffer) -> bool:
        # returns True if new buffer is splitted into multiple months

        last_t = buffer.last_time
        month_k = get_month_key(buffer.first_time)

        if month_k != (last_t.year, last_t.month):
            mid = len(buffer) // 2
            # print(mid) #DUBUG
            self.append(Buffer(buffer.get_lines(0, mid - 1)))
            self.append(Buffer(buffer.get_lines(mid, -1)))
            return True
        
        curr_month_data = self._out_data.get(month_k, [])
        curr_month_data.append(buffer)
        self._out_data[month_k] = curr_month_data

        return False

    def write(self):
        # Now JUST APPEND at the end of the file
        # could be multithreaded

        sorted_out_data = sorted(self._out_data.items(), key=lambda x: x[0])

        for (year, month), buffers in sorted_out_data:
            f_name = log_file_name(year,
                                   month, 
                                   self.__dir_path,
                                   self.__log_name)
            with open(f_name, "a+") as f:
                for buffer in buffers:
                    for line in buffer:
                        f.write(line)
                    
    def clear(self):
        self._out_data = {}


"""
========== FUNCTIONS ==========
"""

def get_time(log_entry: str) -> Optional[dt.datetime]:
    match = RE_PROG_TIME.search(log_entry)
    if match is None:
        return None
    
    return dt.datetime.strptime(match.group(1), LOG_DT_FORMAT)


def get_month_key(time: dt.datetime) -> Tuple[int, int]:
    return(time.year, time.month)


def log_file_name(year: int, month: int, dir_path:str, log_name: str) -> str:
    return f"{dir_path}/{year}-{month:02d}-{log_name}.log"


def get_first_sec_in_year(year: int, tzinfo: Optional[dt.tzinfo] = None) -> dt.datetime:
        return dt.datetime(year, 1, 1, 0, 0, 0,tzinfo=tzinfo)


def get_last_sec_in_year(year: int, tzinfo: Optional[dt.tzinfo] = None) -> dt.datetime:
        return dt.datetime(year, 12, 31, 23, 59, 59,tzinfo=tzinfo)


def buffer_generator(input_path: str, buffer_size: int = 1000) -> Iterator[Buffer]:
    with open(input_path, "r") as input:
        buffer = []

        for line in input:
            buffer.append(line)

            if len(buffer) == buffer_size:
                yield Buffer(buffer)
                buffer = []
        
        if len(buffer) > 0:
            yield Buffer(buffer)


def count_while(buffer: Buffer,
                   predicate: Callable[[dt.datetime], bool])\
        -> int:
    i = 0

    for line in buffer:
        time = get_time(line)

        if time is None or not predicate(time):
            buffer.stop_iter()
        else:
            i += 1
    
    return i

def process_log_file(log_path: str, writer: Writer):
    for buffer in buffer_generator(log_path):
        writer.append(buffer)


        
"""
========== MAIN ==========
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Copies entries from given log files to backup log files.')
    parser.add_argument('-f', '--files-list', dest="log_files", nargs='+', default=[], required=True)
    parser.add_argument('-c', '--configuration-file', dest="config_file")
    parser.add_argument('-n', '--log_name', dest="log_name", required=True)
    parser.add_argument('-d', '--dir_path', dest="dir_path")

    return parser.parse_args()

def main() -> int:
    args = parse_args()

    dir_path = DIR_PATH if args.dir_path is None else args.dir_path
    writer = Writer(dir_path, args.log_name)
    
    for log_file in args.log_files:
        for buffer in buffer_generator(log_file):
            # TODO: check time stamp
            writer.append(buffer)
    
    writer.write()


if __name__ == "__main__":
    main()


        







