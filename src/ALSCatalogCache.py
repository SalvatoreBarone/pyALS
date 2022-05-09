"""
Copyright 2021-2022 Salvatore Barone <salvatore.barone@unina.it>

This is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free
Software Foundation; either version 3 of the License, or any later version.

This is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along with
RMEncoder; if not, write to the Free Software Foundation, Inc., 51 Franklin
Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""
import sqlite3
from .Utility import *


class ALSCatalogCache:
    def __init__(self, file_name):
        self.__file_name = file_name

    def init(self):
        try:
            connection = sqlite3.connect(self.__file_name)
            cursor = connection.cursor()
            cursor.execute("create table if not exists luts (spec text not null, distance integer not null, synth_spec text, S text, P text, out_p integer, out integer, depth integer, primary key (spec, distance))")
            connection.commit()
            connection.close()
        except sqlite3.Error as e:
            print(e)
            exit()

    def get_all_exact_luts(self):
        try:
            connection = sqlite3.connect(self.__file_name)
            cursor = connection.cursor()
            cursor.execute(f"select synth_spec, S, P, out_p, out, depth from luts where distance = 0;")
            specs = []
            while item := cursor.fetchone():
                specs.append((item[0], string_to_nested_list_int(item[1]), string_to_nested_list_int(item[2]), item[3], item[4], item[5]))
            return specs
        except sqlite3.Error as e:
            print(e)
            exit()

    def get_lut_at_dist(self, spec, dist):
        try:
            connection = sqlite3.connect(self.__file_name)
            cursor = connection.cursor()
            cursor.execute(f"select synth_spec, S, P, out_p, out, depth from luts where spec = '{spec}' and distance = {dist};")
            result = cursor.fetchone()
            connection.close()
            if result is not None:
                return result[0], string_to_nested_list_int(result[1]), string_to_nested_list_int(result[2]), result[3], result[4], result[5]
            return None
        except sqlite3.Error as e:
            print(e)
            exit()

    def add_lut(self, spec, dist, synth_spec, S, P, out_p, out, depth):
        try:
            connection = sqlite3.connect(self.__file_name)
            cursor = connection.cursor()
            cursor.execute(f"insert or ignore into luts (spec, distance, synth_spec, S, P, out_p, out, depth) values ('{spec}', {dist}, '{synth_spec}', '{S}', '{P}', {out_p}, {out}, {depth});")
            connection.commit()
            connection.close()
        except sqlite3.Error as e:
            print(e)
            exit()

    def add_luts(self, luts):
        try:
            connection = sqlite3.connect(self.__file_name)
            cursor = connection.cursor()
            for lut in luts:
                cursor.execute(f"insert or ignore into luts (spec, distance, synth_spec, S, P, out_p, out, depth) values ('{lut[0]}', {lut[1]}, '{lut[2]}', '{lut[3]}', '{lut[4]}', {lut[5]}, {lut[6]}, {lut[7]});")
            connection.commit()
            connection.close()
        except sqlite3.Error as e:
            print(e)
            exit()

    def del_lut(self, spec, dist):
        try:
            connection = sqlite3.connect(self.__file_name)
            cursor = connection.cursor()
            cursor.execute(f"delete from luts where spec = '{spec}' and distance =  {dist}")
            connection.commit()
            connection.close()
        except sqlite3.Error as e:
            print(e)
            exit()