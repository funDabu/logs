import argparse
import os
import sys
import datetime as dt
import re
import json


"""
========== TYPES ==========
"""

from typing import TextIO, Optional, List, Generator, Iterator, Iterable, Tuple, Dict, Callable
# Generator[yield_type, send_type, return_type]

TimeInterval = Tuple[dt.datetime, dt.datetime]
CollisionJson = Tuple[Tuple[str, str], int, int]

"""
========== CONSTANTS ==========
"""

from constants import TIME_REGEX, DT_FORMAT, LOG_DT_FORMAT

RE_PROG_TIME = re.compile(TIME_REGEX)

DEF_FUSE_DELIM = 3600 # in seconds
DIR_PATH = "../backup"


"""
========== CLASSES ==========
"""

class Buffer:
    def __init__(self, lines: List[str] = []):
        self._lines: List[str] = lines
        self._head_i = 0
        self._end_i = len(lines) - 1

        self.__locked: bool
        self.__i: int
        self.__stop_i: int
        self.stop_iter() # set default values to previous 3 attributes

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
    
    def __iter__(self, max_n: Optional[int] = None) -> "Buffer":
        # Meaby remove max_n functionality
        self.__locked = True
        self.__i = self._head_i

        self.__stop_i = self._end_i + 1
        if max_n is not None:
            self.__stop_i = min(self.__i + max_n, self.__stop_i)

        return self
    
    def __next__(self) -> str:
        if self.__i < self.__stop_i:
            self.__i += 1
            return self._lines[self.__i - 1]

        self.__locked = False
        raise StopIteration
    
    def stop_iter(self) -> None:
        self.__locked = False
        self.__i = self._end_i + 1
        self.__stop_i = self._head_i - 1

    def __len__(self) -> int:
        return self._end_i - self._head_i + 1


class Collision:
    __slots__ = ["interval", "first_line", "length"]

    def __init__(self, interval:TimeInterval, first_line: int, length: int):
        self.interval: TimeInterval = interval
        self.first_line = first_line
        self.length = length
    
    @classmethod
    def from_json(cls, data: CollisionJson) -> "Collision":

        interval = (dt.datetime.strptime(data[0][0], DT_FORMAT),
                    dt.datetime.strptime(data[0][1], DT_FORMAT) )
        
        return cls(interval, data[1], data[2])
    
    def to_json(self) -> CollisionJson:
        str_interval = (self.interval[0].__format__(DT_FORMAT),
                        self.interval[1].__format__(DT_FORMAT))
        
        return [str_interval, self.first_line, self.length]

    def __len__(self) -> int:
        return self.length
    
    def __lt__(self, obj: "Collision") -> bool:
        return self.interval[0] < obj.interval[1]


class Collisions:
    def __init__(self, file_path: Optional[str]):
        self._data: Dict[int, List[Collision]]

        if file_path is not None:
            self.load_collosions(file_path)
    
    def load_collosions(self, file_path: str) -> None:
        with open(file_path, "r") as f:
            self.from_json(json.load(f))
    
    def from_json(self, data: Dict[str, List[CollisionJson]]) -> None:
        #TODO: OTESTOVAT
        self._data = {int(year) : list(map(Collision.from_json, collisions))
                            for year, collisions in data.items()}
    
    def save_collisions(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump(self.json(), f)
    
    def json(self) -> Dict[int, List[CollisionJson]]:
        #TODO: OTESTOVAT
        return {year : list(map(lambda x: x.to_json(), intervals))
                        for year, intervals in self._data.items()}
    
    def get_year(self, year: int) -> Optional[List[Collision]]:
        return self._data.get(year)
    
    def new_year(self, year: int, tzinfo: Optional[dt.tzinfo] = None) -> None:
        self.add_collision(year,
                          (get_first_sec_in_year(year, tzinfo),)*2,
                          0,
                          DEF_FUSE_DELIM)
        self.add_collision(year, 
                          (get_last_sec_in_year(year,tzinfo),)*2, 
                          0,
                          DEF_FUSE_DELIM)

    def add_collision(self, 
                      year:int,
                      interval: TimeInterval,
                      length: int,
                      fuse_delim: int = 0)\
            -> bool:
        #TODO: OTESTOVAT

        if interval[0].year != interval[1].year:
            return False
        
        year_data = self._data.get(year, [])
        new_coll = Collision(interval, 0, length)
        i = 0

        for coll in year_data:
            if coll.interval[1] <= new_coll.interval[0]:
                new_coll.first_line += coll.length
                i += 1
            elif coll.interval[0] >= new_coll.interval[1]:
                coll.first_line += new_coll.length
            else:
                return False

        year_data.insert(i, new_coll)
        self._data[year] = year_data
        # self.fuse(year, fuse_delim)

        return True
    
    def add_coll_from_buffer(self, buffer:Buffer, fuse_delim: int = 0) -> bool:
        year = buffer.first_time.year
        interval = (buffer.first_time, buffer.last_time)

        return self.add_collision(year, interval, len(buffer), fuse_delim)
    
    def fuse(self,
             year: Optional[int] = None,
             delim: int = DEF_FUSE_DELIM)\
            -> None:
        # year atrib doesnt do anything now
        for year in self._data.keys():
            colls = self._data[year]
            new_colls = []

            # # DEBUG
            # colls_iter = iter(colls)
            # print(f"year: {year}")
            # for coll in colls_iter:
            #     print(coll.to_json())
            # # DEBUG
            

            colls_iter = iter(colls)
            last = next(colls_iter)

            for coll in colls_iter:
                # print(last.to_json(), coll.to_json()) # DEBUG
                # print(last.interval[1], coll.interval[0]) # DEBUG

                if abs(last.interval[1] - coll.interval[0]) < dt.timedelta(seconds=delim):
                    # print(abs(last.interval[1] - coll.interval[0])) # DEBUG!
                    # print() # DEBUG
                    last.length += coll.length
                    last.interval = (last.interval[0], coll.interval[1])
                else:
                    new_colls.append(last)
                    last = coll
            
            new_colls.append(last)
            # print(list(map(lambda x: x.to_json(), new_colls))) # DUBUG
            self._data[year] = new_colls
    

class Writer:
    def __init__(self, dir_path: str, log_name: str) -> None:
        self.__dir_path = os.path.realpath(dir_path)
        self.__log_name = log_name
        self._out_data: Dict[Tuple[int, int], List[Buffer]] = {}
    
    def append(self, buffer: Buffer) -> None:

        last_t = buffer.last_time
        month_k = get_month_key(buffer.first_time)

        if month_k != (last_t.year, last_t.month):
            mid = len(buffer) // 2
            # print(mid) #DUBUG
            self.append(Buffer(buffer.get_lines(0, mid - 1)))
            self.append(Buffer(buffer.get_lines(mid, -1)))
            return
        
        curr_month_data = self._out_data.get(month_k, [])
        curr_month_data.append(buffer)
        self._out_data[month_k] = curr_month_data

    """
    def append(self, buffer: Buffer) -> None:

    # version with liniear finding of next month:

        last_t = buffer.last_time
        month_k = get_month_key(buffer.first_time)
        curr_month_data = self._out_data.get(month_k, [])

        while month_k != (last_t.year, last_t.month):
            new_buffer = []
            month = get_month_key(buffer.first_time)

            while month == month_k:
                # could be better by divide and conquer
                new_buffer.append(buffer.pop_left())
                month = get_month_key(buffer.first_time)

            curr_month_data.append(Buffer(new_buffer))
            self._out_data[month_k] = curr_month_data

            month_k = month
            curr_month_data = self._out_data.get(month_k, [])
        
        curr_month_data.append(buffer)
        self._out_data[month_k] = curr_month_data
    """

    def write(self, collisions: Optional[Collisions] = None):
        # Now JUST APPEND at the end of the file
        sorted_out_data = sorted(self._out_data.items(), key=lambda x: x[0])

        for (year, month), buffers in sorted_out_data:
            f_name = log_file_name(year,
                                   month, 
                                   self.__dir_path,
                                   self.__log_name)
            with open(f_name, "a+") as f:

                i = 0
                for buffer in buffers:
                    i +=1 
                    if collisions is not None\
                       and not collisions.add_coll_from_buffer(buffer):
                        print(f"A {i}-th buffer in {year}-{month} collides "
                              "with collisions", file=sys.stderr)
                        continue

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


def append_avoiding_collisions(buffer:Buffer,
                              writer: Writer,
                              collisions: Collisions)\
        -> Generator[None, Buffer, None]:

    ft, lt = buffer.first_time, buffer.last_time
    start = get_first_sec_in_year(ft.year, ft.tzinfo)
    
    while True:
        if collisions.get_year(ft.year) is None:
            collisions.new_year(ft.year, ft.tzinfo)

        for col in collisions.get_year(ft.year):
            t1, t2 = col.interval[0], col.interval[1]

            if ft < start:
                # pop left while datetime < start
                p1: Callable[[dt.datetime], bool] = lambda t: t < start
                buffer.pop_left(count_while(buffer, p1))

            while lt <= t1:
                # write whole buffer
                writer.append(buffer)

                buffer = yield # ask for new buffer
                ft, lt = buffer.first_time, buffer.last_time
            
            # write entries up to t1
            p2: Callable[[dt.datetime], bool] = lambda t: t <= t1
            n = count_while(buffer, p2)

            writer.append(Buffer(buffer.get_lines(0, n)))
            buffer.pop_left(n)
            ft, lt = buffer.first_time, buffer.last_time

            start = t2


def append_at_and(buffer:Buffer,
                  writer: Writer,
                  collisions: Collisions)\
        -> Generator[None, Buffer, None]:

    ft, lt = buffer.first_time, buffer.last_time
    
    while True:
        if collisions.get_year(ft.year) is None:
            collisions.new_year(ft.year, ft.tzinfo)
        current_year_colls = collisions.get_year(ft.year)

        start = get_first_sec_in_year(ft.year, ft.tzinfo)
        end = get_last_sec_in_year(ft.year, ft.tzinfo)
        if len(current_year_colls) > 2:
            start = current_year_colls[-2].interval[1]
        
        # pop left while datetime < start
        p1: Callable[[dt.datetime], bool] = lambda t: t < start
        buffer.pop_left(count_while(buffer, p1))
    
        while lt <= end:
                # write whole buffer
                writer.append(buffer)

                buffer = yield # ask for new buffer
                ft, lt = buffer.first_time, buffer.last_time

        # append rest of the year
        p2: Callable[[dt.datetime], bool] = lambda t: t <= end
        n = count_while(buffer, p2)

        writer.append(Buffer(buffer.get_lines(0, n)))
        buffer.pop_left(n)
        ft, lt = buffer.first_time, buffer.last_time
        
"""
========== MAIN ==========
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Copies entries from given log files to backup log files.')
    parser.add_argument('-f', '--files-list', dest="log_files", nargs='+', default=[])
    parser.add_argument('-c', '--configuration-file', dest="config_file")
    parser.add_argument('-n', '--log_name', dest="log_name")

    return parser.parse_args()

def main() -> int:
    args = parse_args()

    if not os.path.exists(args.config_file):
        print("config file does not exists", file=sys.stderr)
        return 1

    collisions = Collisions(args.config_file)
    writer = Writer(DIR_PATH, args.log_name)
    
    for file in args.log_files:
        buffer_gen = buffer_generator(file)
        buffer: Buffer

        try:
            buffer = next(buffer_gen)
        except StopIteration:
            break
        
        appender = append_at_and(buffer, writer, collisions)
        next(appender)

        for buffer in buffer_gen:
            appender.send(buffer)
        
        appender.close()
        writer.write(collisions)
        # print(collisions.json()) #DEBUG
        writer.clear()
        collisions.fuse()

    collisions.save_collisions(args.config_file)

if __name__ == "__main__":
    main()


        







