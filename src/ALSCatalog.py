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
      print(sqlite3.version)
      self.__init_db()
      print("Database created and successfully connected to SQLite")
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
  @returns An appropriate set of catolog entries, as a list of list. The catalog is structured as follows:
   - Each element of the returned list is a list containing catalog entries for a given LUT specification
   - Each entry of the 2nd-level list is a function specification at a determined Hamming distance from the original
     non-approximate specification i.e. the element position within the list gives the Hamming distance from the 
     original specification; therefore, elements in position [0] represent non-approximate function specification.
  Example:
  [
    # LUT specs
    [
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)}, <-- non-approx. specification
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)}, <-- approx-spec at distance 1
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)}, <-- approx-spec at distance 2
      ...
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)}  <-- approx-spec at distance N
    ],
    # LUT specs
    [
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)},
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)},
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)},
      ...
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)}
    ],
    ...
    # LUT specs
    [
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)},
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)},
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)},
      ...
      {"spec": function specification (string), "gates" : AND-gates required to synthesize the spec (integer)}
    ]
  ]

  @note This class implements LUT caching, so the actual synthesis of a LUT is performed i.f.f. the latter is not yet
  in the database.
  """
  def generate_catalog(self, design):
    # Building the set of unique luts
    luts_set = set()
    for module in design.selected_whole_modules_warn():
      for cell in module.selected_cells():
        if ys.IdString("\LUT") in cell.parameters:     
          luts_set.add(cell.parameters[ys.IdString("\LUT")])

    # TODO: This for loop should be partitioned among multiple threads. 
    #! Make sure the db connection object can be safely shared among processes
    catalog = []
    for lut in luts_set:
      lut_specifications = []
      # Sinthesizing the baseline (non-approximate) LUT
      hamming_distance = 0;
      synt_spec, gates = self.get_synthesized_lut(lut, hamming_distance)
      lut_specifications.append({"spec": synt_spec, "gates": gates})
      #  and, then, approximate ones
      while gates > 0:
        hamming_distance += 1
        synt_spec, gates = self.get_synthesized_lut(lut, hamming_distance)
        lut_specifications.append({"spec": synt_spec, "gates": gates})
      catalog.append(lut_specifications)
    return catalog

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
  def get_synthesized_lut(self, lut_spec, distance):
    result = self.__get_lut_at_dist(lut_spec, distance)
    if result is None:
      ys.log("Cache miss for {spec}@{dist}\n".format(spec = lut_spec.as_string(), dist = distance))
      ys.log("Performing SMT-ES for {spec}@{dist} ...".format(spec = lut_spec.as_string(), dist = distance))
      synth_spec, gates = ALSSMT(lut_spec, distance, self.__es_timeout).synthesize()
      ys.log(" ...Done! {spec}@{dist} satisfied using {gates} gates. Synth. spec.: {synth_spec}\n".format(spec = lut_spec.as_string(), dist = distance, synth_spec = synth_spec, gates = gates))
      self.__add_lut(lut_spec, distance, synth_spec, gates)
      return synth_spec, gates
    else:
      ys.log("Cache hit for {spec}@{dist}, which is implemented as {synth_spec} using {gates} gates\n".format(spec = lut_spec.as_string(), dist = distance, synth_spec = result[0], gates = result[1]))
      return result[0], result[1]

  """ 
  @brief Inits the database
  """
  def __init_db(self):
    self.__cursor.execute("create table if not exists luts (spec text not null, distance integer not null, synth_spec text, gates integer, primary key (spec, distance))")
    self.__connection.commit()
  
  """
  @brief Queries the database for a particular lut specification. 
  """
  def __get_lut_at_dist(self, spec, dist):
    self.__cursor.execute("select synth_spec, gates from luts where spec = '{spec}' and distance = {dist};".format(spec = spec, dist = dist))
    return self.__cursor.fetchone()

  """
  @brief Insert a synthesized LUT into the database
  """
  def __add_lut(self, spec, dist, synth_spec, gates):
    self.__cursor.execute("insert into luts (spec, distance, synth_spec, gates) values ('{spec}', {dist}, '{synth_spec}', {gates});".format(spec = spec, dist = dist, synth_spec = synth_spec, gates = gates))
    self.__connection.commit()
    