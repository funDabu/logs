import sqlite3
import datetime as dt
from typing import Optional, Tuple

from constants import DATE_FORMAT

class GeolocDB:
    def __init__(self, path: str):
        self._path = path
        self.__cur = None
        self.__con = None

    def conntect(self):
        self.__con = sqlite3.connect(self._path)
        self.__cur = self.__con.cursor()

        if self._is_empty():
            self._create_geoloc_table()

    def _is_empty(self):      
        res = self.__cur.execute("SELECT name FROM sqlite_master WHERE name='geolocations'")
        return res.fetchone() is None

    def _create_geoloc_table(self):
        self.__cur.execute("CREATE TABLE geolocations(ip, geolocation, timestamp)")
        self.__cur.execute("CREATE INDEX index_geolocations ON geolocations (ip)")
    
    def get_geolocation(self, ip: str) -> Optional[Tuple(str,str)]:
        if self.__cur is None:
            self.conntect()

        res = self.__cur.execute("SELECT geolocation, timestamp FROM geolocations WHERE ip='?'", ip)
        return res.fetchone()

    def insert_geolocation(self, ip:str, geolocation:str):
        if self.__cur is None:
            self.conntect()

        date = dt.date.today()
        self.__cur.execute("INSERT INTO geolocations VALUES(?)",
                           (ip, geolocation, date.__format__(DATE_FORMAT)))


    
