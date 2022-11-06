from constants import TIME_REGEX, DT_FORMAT, LOG_DT_FORMAT
import argparse
import os
import sys
import datetime as dt
import re
import json


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
        if self._head_i >= self.__len__():
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
        if self.__locked or self.__len__() < n:
            return

        self._head_i += n
        self.__set_first()
        return self._lines[self._head_i - 1]

    def peek_left(self):
        if self.__len__() > 0:
            return self._lines[self._head_i]

    def get(self, n: int, default: Optional[str] = None) -> Optional[str]:
        if self._head_i <= n <= self._end_i:
            return self._lines(n)
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

    @classmethod
    def from_json(cls, data: str) -> "TimeStamp":
        time = get_time(data)
        return cls(time, data)

    def to_json(self) -> str:
        return self.log_entry 

class TimeStamps:
    def __init__(self, file_path: Optional[str]):
        self._data: Dict[Tuple[int, int], List[TimeStamp]]
        self.file_path = file_path

        if file_path is not None:
            self.load_timestamps(file_path)

    def load_timestamps(self, file_path: str) -> None:
        with open(file_path, "r") as f:
            self.from_json(json.load(f))

    def _key_from_str(key_str: str) -> Tuple[int, int]:
        splited = key_str.split('-')
        assert len(splited) == 2

        return tuple(map(int, splited))

    def _key_to_str(key: Tuple[int, int]) -> str:
        return f"{key[0]}-{key[1]}"

    def from_json(self, data: Dict[str, List[TimeStamp]]) -> None:
        #TODO: OTESTOVAT
        self._data = {self._key_from_str(key): list(map(TimeStamp.from_json, tss))
                      for key, tss in data.items()}

    def save_timestamps(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump(self.json(), f)

    def json(self) -> Dict[int, List[TimeStamp]]:
        #TODO: OTESTOVAT
        return {self._key_to_str(key): list(map(TimeStamp.to_json, tts))
                for key, tts in self._data.items()}

    def get(self,
            key: Tuple[int, int],
            default: Optional[TimeStamp] = None)\
            -> Optional[TimeStamp]:
        return self._data.get(key, default)


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
    return (time.year, time.month)


def log_file_name(year: int, month: int, dir_path: str, log_name: str) -> str:
    return f"{dir_path}/{year}-{month:02d}-{log_name}.log"


def get_first_sec_in_year(year: int, tzinfo: Optional[dt.tzinfo] = None) -> dt.datetime:
    return dt.datetime(year, 1, 1, 0, 0, 0, tzinfo=tzinfo)


def get_last_sec_in_year(year: int, tzinfo: Optional[dt.tzinfo] = None) -> dt.datetime:
    return dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=tzinfo)


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
    return abs(time1 - time2) <= dt.timedelta(seconds=range)


def signif_older(test_time: dt.datetime,
                 timestamp: dt.datetime,
                 time_range: int = TIME_PROXI_RANGE)\
        -> bool:
    return not in_time_proximity(test_time, timestamp, time_range)\
           and test_time < timestamp


def check_timestamp(buffer: Buffer, tss: TimeStamps) -> Tuple[bool, Buffer]:
    # return [True, buffer] if 
    #   - timestamp was found, 
    #       than buffer contains only entries younfer than the ts
    #   - first entry is significantly younger than timestamp,
    #       than buffer contains all entries
    # retrurns [False, buffer] otherwise
    #   - buffer is empty if its last entry is signif. older than timestamp
    #   - otherwise siginf. older values are filtered from buffer one by one 
    # 
    # siginficatnly younger means its time is after timestamp + TIME_PROXI_RANGE

    ts = tss.get(get_month_key(buffer.first_time))

    if not in_time_proximity(buffer.first_time, ts.dtime)\
       and buffer.first_time > ts.dtime:
        return (True, buffer)  # significantly younger than ts

    if signif_older(buffer.last_time, ts.dtime):
        return (False, Buffer([]))

    new_buffer = []
    for i, line in enumerate(buffer):
        if line == ts.log_entry:
            buffer.pop_left(i + 1)
            return (True, buffer)

        time = get_time(line)
        assert time is not None

        if not signif_older(time, ts.dtime):
            new_buffer.append(line)

    # timestap was not found
    return(False, Buffer(new_buffer))


def process_log_file(log_path: str, writer: Writer):
    for buffer in buffer_generator(log_path):
        writer.append(buffer)


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
