from constants import TIME_REGEX, DT_FORMAT, LOG_DT_FORMAT
import argparse
import os
import sys
import datetime as dt
import re
import gzip


"""
========== TYPES ==========
"""

from typing import TextIO, Optional, List, Iterator, Iterable, Tuple, Dict, Callable

"""
========== CONSTANTS ==========
"""


RE_PROG_TIME = re.compile(TIME_REGEX)

TIME_PROXI_RANGE = 60  # in seconds
DIR_PATH = "."  # default output directory


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
        if self._head_i > self._end_i:
            self.first_time = None
            return

        self.first_time = get_time(self._lines[self._head_i])

    def __set_last(self) -> None:
        self.last_time = get_time(self._lines[self._end_i])

    def get_lines(self, start: int, end: int) -> List[str]:
        # result includes idices start and end
        end = self._end_i if end == -1 else\
            min(self._end_i, end + self._head_i)

        return self._lines[self._head_i + start: end + 1]

    def pop_left(self, n: int = 1) -> Optional[str]:
        if self.__locked or n < 1:
            return

        new_head = min(self._head_i + n, self._head_i + self.__len__())
        self._head_i = new_head
        self.__set_first()
        return self._lines[self._head_i - 1]

    def peek_left(self):
        if self.__len__() > 0:
            return self._lines[self._head_i]

    def get(self, n: int, default: Optional[str] = None) -> Optional[str]:
        n = self._end_i if n == -1 else n

        if self._head_i <= n <= self._end_i:
            return self._lines[n]
        return default

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


class TimeStamp:
    __slots__ = ["dtime", "log_entry"]

    def __init__(self, dtime: dt.datetime, log_entry: str):
        self.dtime = dtime
        self.log_entry = log_entry
    
    def update_time(self) -> None:
        self.dtime = get_time(self.log_entry)

    @classmethod
    def from_json(cls, data: str) -> "TimeStamp":
        if data == "":
            time = dt.datetime.strptime("01/Jan/1980:00:00:00 +0000",
                                        LOG_DT_FORMAT)
        else:
            time = get_time(data)
        return cls(time, data)

    def to_json(self) -> str:
        return self.log_entry 

class Reporter:
    def __init__(self, buffer_size = 1000) -> None:
        self.eliminated_lines_count = 0
        self.buffer_size = buffer_size
        return
    
    def count_eliminated_line(self, buffer:Buffer, orig_len: int = -1) -> None:
        orig_len = self.buffer_size if orig_len < 0 else orig_len

        assert orig_len - len(buffer) >= 0
        # print(f"just eliminated {orig_len - len(buffer)} lines") # DEBUG
        self.eliminated_lines_count += orig_len - len(buffer)
    
    def report(self, output: TextIO = sys.stderr) -> None:
        print("Number of eliminated lines so far:",
               self.eliminated_lines_count,
               file=output)

class Writer:
    def __init__(self, dir_path: str, log_name: str) -> None:
        self.__dir_path = os.path.realpath(dir_path)
        self.__log_name = log_name
        self._out_data: Dict[Tuple[int, int], List[Buffer]] = {}

    def append(self, buffer: Buffer) -> bool:
        # returns True if new buffer is splitted into multiple months
        if len(buffer) == 0:
            return False

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

    def write(self, ts: Optional[TimeStamp] = None):
        # Now JUST APPEND at the end of the file
        # could be multithreaded

        sorted_out_data = sorted(self._out_data.items(), key=lambda x: x[0])
        last_log: Optional[str] = None

        for (year, month), buffers in sorted_out_data:
            f_name = log_file_name(year,
                                   month,
                                   self.__dir_path,
                                   self.__log_name)
            with open(f_name, "a+") as f:
                for buffer in buffers:
                    for line in buffer:
                        f.write(line)
                    last_log = buffer.get(-1)
        
        if ts is not None and last_log is not None:
            ts.log_entry = last_log
            ts.update_time()

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
    return (time.year, time.month)


def log_file_name(year: int, month: int, dir_path: str, log_name: str) -> str:
    return f"{dir_path}/{year}-{month:02d}-{log_name}.log"


def get_first_sec_in_year(year: int, tzinfo: Optional[dt.tzinfo] = None) -> dt.datetime:
    return dt.datetime(year, 1, 1, 0, 0, 0, tzinfo=tzinfo)


def get_last_sec_in_year(year: int, tzinfo: Optional[dt.tzinfo] = None) -> dt.datetime:
    return dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=tzinfo)


def buffer_generator(input_path: str, buffer_size: int = 1000) -> Iterator[Buffer]:
    if input_path.split(".")[-1] == "gz":
        open_func = gzip.open
    else:
        open_func = open

    with open_func(input_path, "rt") as input:
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

    def predicate(line: str, p=predicate) -> bool:
        time = get_time(line)
        return time is not None and p(time)

    return count_while_general(buffer, predicate)


def count_while_general(buffer: Buffer,
                        predicate: Callable[[str], bool])\
        -> int:

    i = 0

    for line in buffer:
        if not predicate(line):
            buffer.stop_iter()
        else:
            i += 1

    return i


def in_time_proximity(time1: dt.datetime, time2: dt.datetime,
                      time_range=TIME_PROXI_RANGE) -> bool:
    return abs(time1 - time2) <= dt.timedelta(seconds=time_range)


def signif_older(test_time: dt.datetime,
                 timestamp: dt.datetime,
                 time_range: int = TIME_PROXI_RANGE)\
        -> bool:
    return not in_time_proximity(test_time, timestamp, time_range)\
           and test_time < timestamp


def signif_younger(test_time: dt.datetime,
                   timestamp: dt.datetime,
                   time_range: int = TIME_PROXI_RANGE)\
        -> bool:
    return not in_time_proximity(test_time, timestamp, time_range)\
           and test_time > timestamp


def check_timestamp(buffer: Buffer, ts: TimeStamp) -> Tuple[bool, Buffer]:
    # return [True, buffer] if 
    #   - timestamp was found and
    #       buffer contains only entries younfer than the ts
    # returns [False, buffer] otherwise,
    #   siginf. older values are filtered from buffer one by one 
    # 
    # siginficatnly younger means its time is after timestamp + TIME_PROXI_RANGE

    new_buffer = []
    for i, line in enumerate(buffer):
        if line == ts.log_entry:
            buffer.stop_iter()
            buffer.pop_left(i + 1)

            # print("timestamp found on buffer index", i) # DEBUG
            # print(len(buffer)) # DUBUG

            return (True, buffer)

        time = get_time(line)
        assert time is not None

        if not signif_older(time, ts.dtime):
            new_buffer.append(line)

    # timestap was not found
    # print("timestamp not found") # DEBUG
    return(False, Buffer(new_buffer))



def process_log_file(log_path: str, writer: Writer, ts: TimeStamp) -> None:
    ts_reached = False

    reporter = Reporter()

    for buffer in buffer_generator(log_path):
        orig_buffer_len = len(buffer)

        if not ts_reached and len(buffer) > 0:
            if signif_younger(buffer.first_time, ts.dtime):
                ts_reached = True
            elif signif_older(buffer.last_time, ts.dtime):
                buffer = Buffer([])
            elif check_timestamp(buffer, ts):
                writer.clear()
        
        reporter.count_eliminated_line(buffer, orig_buffer_len)
        writer.append(buffer)
    
    reporter.report()


"""
========== MAIN ==========
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Copies entries from given log files to backup log files.')
    parser.add_argument('-f', '--files-list', dest="log_files",
                        nargs='+', default=[], required=True)
    parser.add_argument('-c', '--configuration-file', dest="config_file")
    parser.add_argument('-n', '--log_name', dest="log_name", required=True)
    parser.add_argument('-d', '--dir_path', dest="dir_path")

    return parser.parse_args()


def main():
    args = parse_args()

    dir_path = DIR_PATH if args.dir_path is None else args.dir_path
    writer = Writer(dir_path, args.log_name)

    timestamp: TimeStamp
    with open(args.config_file, "r") as f:
        timestamp = TimeStamp.from_json(f.read())


    for log_file in args.log_files:
        # Assumes log files are ordered from younger to older log file
        process_log_file(log_file, writer, timestamp)

    writer.write(timestamp)
    with open(args.config_file, "w") as f:
        f.write(timestamp.to_json())



if __name__ == "__main__":
    main()
