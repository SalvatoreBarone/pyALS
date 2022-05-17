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
import math, random, sys
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
					spec = cell.parameters[ys.IdString("\LUT")].as_string()[::-1]
					if negate(spec) not in luts_set:
						luts_set.add(spec)
		luts_set = list(luts_set)
		random.shuffle(luts_set)
		luts_sets = list_partitioning(luts_set, cpu_count())
		args = [ [self.__cache_file, lut_set, es_timeout, self.__solver] for lut_set in luts_sets ]
		with Pool(cpu_count()) as pool:
			catalog = pool.starmap(generate_catalog, args)
		catalog = [ item for sublist in catalog for item in sublist ]
		return catalog


def generate_catalog(catalog_cache_file, luts_set, smt_timeout, solver):
	cache = ALSCatalogCache(catalog_cache_file)
	catalog = []
	for lut_conf in luts_set:
		lut_specifications = []
		exact_spec =  cache.get_exact_lut(lut_conf)
		if exact_spec is None:
			print(f"Cache miss for {lut_conf}")
			hamming_distance = 0
			gates = 10000 # large enough
			while gates > 0:
				synt_spec, S, P, out_p, out, depth = do_synthesis(lut_conf, hamming_distance, solver, smt_timeout)
				print(f"{lut_conf}@{hamming_distance} synthesized as {synt_spec} using {len(S[0])} gates at depth {depth}.")
				if len(S[0]) < gates:
					lut_specifications.append({"spec": synt_spec, "gates": len(S[0]), "S": S, "P": P, "out_p": out_p, "out": out, "depth": depth})
					cache.add_lut(lut_conf, hamming_distance, synt_spec, S, P, out_p, out, depth)
				gates = len(S[0])
				hamming_distance += 1
		else:
			synt_spec, S, P, out_p, out, depth = exact_spec
			lut_specifications.append({"spec": synt_spec, "gates": len(S[0]), "S": S, "P": P, "out_p": out_p, "out": out, "depth": depth})
			for lut in cache.get_approx_luts(lut_conf):
				synt_spec, S, P, out_p, out, depth = lut
				lut_specifications.append({"spec": synt_spec, "gates": len(S[0]), "S": S, "P": P, "out_p": out_p, "out": out, "depth": depth})
		catalog.append(lut_specifications)
	return catalog


def synthesize(catalog_cache_file, luts_set, smt_timeout, solver):
	cache = ALSCatalogCache(catalog_cache_file)
	for lut_conf in luts_set:
		hamming_distance = 0
		gates = 10000 # large enough
		while gates > 0:
			print(f"Synthesizing {lut_conf}@{hamming_distance}.")
			synt_spec, S, P, out_p, out, depth = do_synthesis(lut_conf, hamming_distance, solver, smt_timeout)
			print(f"{lut_conf}@{hamming_distance} synthesized as {synt_spec} using {len(S[0])} gates at depth {depth}.")
			if len(S[0]) < gates:
				cache.add_lut(lut_conf, hamming_distance, synt_spec, S, P, out_p, out, depth)
			gates = len(S[0])
			hamming_distance += 1


def do_synthesis(lut_spec, dist, solver, es_timeout):
	synth_spec, S, P, out_p, out = ALSSMT_Z3(lut_spec, dist, es_timeout).synthesize() if solver == ALSConfig.Solver.Z3 else ALSSMT_Boolector(lut_spec, dist, es_timeout).synthesize()
	num_ins = int(math.log2(len(synth_spec))) + 1
	num_nodes = num_ins + len(S[0])
	depth = [0] * num_nodes
	for i, gate in zip(range(num_ins, num_nodes), zip(*S)):
		depth[i] = max(depth[gate[0]], depth[gate[1]]) + 1
	return synth_spec, S, P, out_p, out, depth[-1]
