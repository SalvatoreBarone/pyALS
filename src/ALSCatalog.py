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
import math
import random
from pyosys import libyosys as ys
from multiprocessing import Pool, cpu_count
from .ALSCatalogCache import *
from .ALSSMT import *

class ALSCatalog:
  def __init__(self, file_name, solver):
    self.__cache_file = file_name
    self.__solver = solver
    ALSCatalogCache(self.__cache_file).init()

  def generate_catalog(self, design, es_timeout):
    luts_set = set()
    for module in design.selected_whole_modules_warn():
      for cell in module.selected_cells():
        if ys.IdString("\LUT") in cell.parameters:     
          luts_set.add(cell.parameters[ys.IdString("\LUT")].as_string()[::-1])

    # return generate_catalog(self.__cache_file, luts_set, es_timeout)
    luts_set = list(luts_set)
    random.shuffle(luts_set)
    luts_to_be_synthesized = list_partitioning(luts_set, cpu_count())
    args = [ [self.__cache_file, luts, es_timeout, self.__solver] for luts in luts_to_be_synthesized ]
    with Pool(cpu_count()) as pool:
      catalog = pool.starmap(generate_catalog, args)
    catalog = [ item for sublist in catalog for item in sublist ]
    return catalog

def generate_catalog(catalog_cache_file, luts_set, smt_timeout, solver):
    catalog = []
    for lut in luts_set:
      lut_specifications = []
      # Sinthesizing the baseline (non-approximate) LUT
      hamming_distance = 0
      synt_spec, S, P, out_p, out, depth = get_synthesized_lut(catalog_cache_file, lut, hamming_distance, solver, smt_timeout)
      gates = len(S[0])
      lut_specifications.append({"spec": synt_spec, "gates": gates, "S": S, "P": P, "out_p": out_p, "out": out, "depth": depth})
      #  and, then, approximate ones
      while gates > 0:
        hamming_distance += 1
        synt_spec, S, P, out_p, out, depth = get_synthesized_lut(catalog_cache_file, lut, hamming_distance, solver, smt_timeout)
        gates = len(S[0])
        lut_specifications.append({"spec": synt_spec, "gates": gates, "S": S, "P": P, "out_p": out_p, "out": out, "depth": depth})
      catalog.append(lut_specifications)
      # Speculation...
      # cache = ALSCatalogCache(catalog_cache_file)
      # luts_to_be_added = []
      # for i in range(1, len(lut_specifications)):
      #   luts_to_be_added.append((lut_specifications[i]["spec"], 0, lut_specifications[i]["spec"], lut_specifications[i]["S"], lut_specifications[i]["P"], lut_specifications[i]["out_p"], lut_specifications[i]["out"], lut_specifications[i]["depth"]))
      #   for j in range(i+1, len(lut_specifications)):
      #     luts_to_be_added.append((lut_specifications[i]["spec"], j-i, lut_specifications[j]["spec"], lut_specifications[j]["S"], lut_specifications[j]["P"], lut_specifications[j]["out_p"], lut_specifications[j]["out"], lut_specifications[i]["depth"]))
      # cache.add_luts(luts_to_be_added)
    return catalog

def get_synthesized_lut(cache_file_name, lut_spec, dist, solver, es_timeout):
  cache = ALSCatalogCache(cache_file_name)
  result = cache.get_lut_at_dist(lut_spec, dist)
  if result is None:
    ys.log(f"Cache miss for {lut_spec}@{dist}\n")
    synth_spec, S, P, out_p, out = ALSSMT_Z3(lut_spec, dist, es_timeout).synthesize() if solver == ALSConfig.Solver.Z3 else ALSSMT_Boolector(lut_spec, dist, es_timeout).synthesize()
    gates = len(S[0])
    num_ins = int(math.log2(len(synth_spec))) + 1
    num_nodes = num_ins + gates
    depth = [0] * num_nodes
    for i, gate in zip(range(num_ins, num_nodes), zip(*S)):
      depth[i] = max(depth[gate[0]], depth[gate[1]]) + 1
    print(f"{lut_spec}@{dist} synthesized as {synth_spec} using {gates} gates at depth {depth[-1]}.")
    cache.add_lut(lut_spec, dist, synth_spec, S, P, out_p, out, depth[-1])
    return synth_spec, S, P, out_p, out, depth[-1]
  else:
    return result[0], result[1], result[2], result[3], result[4], result[5]
