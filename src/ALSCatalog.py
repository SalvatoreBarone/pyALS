"""
Copyright 2021 Salvatore Barone <salvatore.barone@unina.it>

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
from pyosys import libyosys as ys
from .ALSSMT import *

class ALSCatalog:
  def __init__(self, file_name, es_timeout):
    self.__connection = None
    self.__es_timeout = es_timeout
    try:
      self.__connection = sqlite3.connect(file_name)
      self.__cursor = self.__connection.cursor()
      print("Database created and successfully connected to SQLite")
      print(sqlite3.version)
      self.__init_db()
    except sqlite3.Error as e:
      print(e)
      exit()

  """
  @brief Catalog generation procedure

  @details
  Starting from the exact specification of each unique LUT in the considered circuit, we progressively increase the
  Hamming distance between the function being implemented by original LUT (cut) and the approximate one, while 
  performing Exact Synthesis. 
  
  The procedure stops when, due to the approximation itself, the synthesis becomes trivial, i.e. it results in a catalog
  entry of size zero.
  """
  def generate_catalog(self, design):
    # Building the set of unique luts
    luts_set = set()
    for module in design.selected_whole_modules_warn():
      for cell in module.selected_cells():
        if ys.IdString("\LUT") in cell.parameters:     
          luts_set.add(cell.parameters[ys.IdString("\LUT")])

    # Sinthesizing the baseline lut and, then, approximate ones
    # TODO: This for loop have to be partitioned among multiple threads. Make sure the db connection object can be safely shared among processes
    for lut in luts_set:
      hamming_distance = 0;
      result = self.get_synthesized_lut(lut, 0)
      while True: #TODO replace True with result.aig.gates > 0
        hamming_distance += 1
        result = self.get_synthesized_lut(lut, hamming_distance)
    # FIXME what do we do with the generated catalog?

  """
  @brief Queries the database for a particular lut specification. 

  @param [in] lut
              exact specification of the lut; combined with distance makes up the actual specification of the 
              synthesized LUT to be searched.

  @param [in] distance
              Hamming distance of the LUT to be searched against the exact specification in lut; combined with the 
              latter makes up the actual specification of the sy thesized to be searched.

  @details 
  If the lut exists, it is returned, otherwise the function performs the exact synthesis of the lut and adds it
  to the catalog before returning it to the caller.
  
  @return If the lut exists, it is returned, otherwise the function performs the exact synthesis of the lut and adds it
  to the catalog before returning it to the caller.
  """
  def get_synthesized_lut(self, lut, distance):
    result = self.__get_lut_at_dist(lut, distance)
    if result is None:
      ys.log("Cache miss for lut " + lut.as_string() + " at distance " + str(distance) + "\n")
      result = self.__synthesize_lut(lut, distance)
      self.__add_lut(lut, result)
    else:
      ys.log("Cache hit for lut " + lut.as_string() + " at distance " + str(distance) + "\n")
    return result

  def __synthesize_lut(self, lut_spec, distance):
    ys.log("Performing exact synthesis for LUT specification " + lut_spec.as_string() + "@" + str(distance) + " ...\n")
    gates, model = ALSSMT(lut_spec, distance, self.__es_timeout).synthesize()
    ys.log(" ...Done! " + lut_spec.as_string() + "@" + str(distance) + " satisfied using " + str(gates) + " gates\n")
    print(model)
    return model

  """ 
  @brief Inits the database
  """
  def __init_db(self):
    self.__cursor.execute("create table if not exists luts (spec text not null, aig blob not null, primary key (spec));")
    self.__connection.commit()
  
  """
  @brief Queries the database for a particular lut specification. 
  """
  def __get_lut_at_dist(self, spec, dist):
    self.__cursor.execute("select aig from luts where spec = '" + str(spec) + "@" + str(dist) + "';")
    return self.__cursor.fetchone()

  """
  @brief Insert a synthesized LUT into the database
  """
  def __add_lut(self, spec, aig):
    self.__cursor.execute("insert into luts (spec, aig) values ('" + str(spec) + "', ?)",  sqlite3.Binary(aig))
    self.__connectionn.commit()
    