import sqlite3
import os
import datetime as dt
from typing import Optional, Tuple

from logs.helpers.constants import DATE_FORMAT, GEOLOC_DB_PATH

class GeolocDB:
    def __init__(self, path: str = GEOLOC_DB_PATH):
        self._path = path
        self.__cursor = None
        self.__connection = None

        path = os.path.realpath(path)
        self.conntect()

    def conntect(self):
        self.__connection = sqlite3.connect(self._path)
        self.__cursor = self.__connection.cursor()

        if self._is_empty():
            self._create_geoloc_table()
    
    def close(self):
        if self.__connection is not None:
            self.__connection.close()

    def _is_empty(self):      
        res = self.__cursor.execute("SELECT name FROM sqlite_master WHERE name='geolocations'")
        return res.fetchone() is None

    def _create_geoloc_table(self):
        self.__cursor.execute("CREATE TABLE geolocations(ip, geolocation, timestamp)")
        self.__cursor.execute("CREATE INDEX index_geolocations ON geolocations (ip)")
    
    def get_geolocation(self, ip: str) -> Optional[Tuple[str,str]]:
        # Assumes only one row for a single ip address
        if self.__cursor is None:
            self.conntect()

        res = self.__cursor.execute("SELECT geolocation, timestamp FROM geolocations WHERE ip=?", [ip])
        return res.fetchone()
    
    def get_all(self) :
        if self.__cursor is None:
            self.conntect()

        res = self.__cursor.execute("SELECT * FROM geolocations")
        return res.fetchall()


    def insert_geolocation(self, ip:str, geolocation:str):
        if self.__cursor is None:
            self.conntect()

        date = dt.date.today()
        self.__cursor.execute("INSERT INTO geolocations VALUES(?, ?, ?)",
                              (ip, geolocation, date.__format__(DATE_FORMAT)))
        self.__connection.commit()


    
