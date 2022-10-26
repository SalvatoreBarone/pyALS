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
import os
from .ALSGraph import *
from .YosysHelper import *
from .ErrorMetrics import *
from .template_render import template_render


class ALSArithModel:
	__resource_dir = "../resources/"
	__library_model_py = "library_model.py.template"
	__single_circuit_model_py = "single_circuit_model.py.template"

	def __init__(self, helper, problem, signal_weights, design_name = "original"):
		dir_path = os.path.dirname(os.path.abspath(__file__))
		self.resource_dir =  f"{dir_path}/{self.__resource_dir}"
		self.lut_model_py = f"{self.resource_dir}{self.__library_model_py}"
		self.single_circuit_model = f"{self.resource_dir}{self.__single_circuit_model_py}"
		self.helper = helper
		self.problem = problem
		self.design_name = design_name
		self.helper.load_design(design_name)
		self.helper.reverse_splitnets()
		self.wires = helper.get_PIs_and_Pos()
		assert len(self.wires["PI"]) == 2, "This circuit has more than two multi-bit primary inputs. This is not supported"
		assert len(self.wires["PO"]) == 1, "This circuit has more than one multi-bit primary output. This is not supported"
		self.pis_weights = [{f"{pi.str()}[{i}]": signal_weights[f"{pi.str()}[{i}]"] for i in range(w.width)} for pi, w in self.wires["PI"].items()]
		for po, w in self.wires["PO"].items():
			self.po_weights = { f"{po.str()}[{i}]": signal_weights[f"{po.str()}[{i}]"] for i in range(w.width)}
	
	def generate_library(self, top_module, pareto_set, destination, use_float):
		items = {"top_module" : top_module,	"lut" : {} } | { f"operand{i+1}" : k.str()[1:] for i, k in zip(range(2), self.wires["PI"].keys())}
		for n, c in enumerate(pareto_set):
			print(f"Generating model {n}/{len(pareto_set)}")
			configuration = self.problem.matter_configuration(c)
			computed_circuit_output = self.problem.get_outputs(configuration)
			model = self.get_lut_for_variant(computed_circuit_output, use_float)
			for k, v in model.items():
				if k not in items["lut"].keys():
					items["lut"][k] = []
				items["lut"][k].append(v)
		template_render(self.resource_dir, self.__library_model_py, items, destination)
  
	def generate_single_circuits(self, top_module, pareto_set, destination, use_float):
		items = {"top_module" : top_module,	"lut" : {} } | { f"operand{i+1}" : k.str()[1:] for i, k in zip(range(2), self.wires["PI"].keys())}
		for n, c in enumerate(pareto_set):
			print(f"Generating model {n}/{len(pareto_set)}")
			configuration = self.problem.matter_configuration(c)
			computed_circuit_output = self.problem.get_outputs(configuration)
			model = self.get_lut_for_variant(computed_circuit_output, use_float)
			items["lut"] = model
			template_render(self.resource_dir, self.__single_circuit_model_py, items, f"{destination}/variant_{n:05d}.py")
  
		
	def get_lut_for_variant(self, computed_circuit_outputs, use_float):
		if use_float:
			return {
				(
					bool_to_value({k : i for k, i in o["i"].items() if k in self.pis_weights[0] }, self.pis_weights[0]), 
					bool_to_value({k : i for k, i in o["i"].items() if k in self.pis_weights[1] }, self.pis_weights[1])
				) 
				: 
				bool_to_value(o["a"], self.po_weights) for o in computed_circuit_outputs 
			}
		else:
			return {
				(
					int(bool_to_value({k : i for k, i in o["i"].items() if k in self.pis_weights[0] }, self.pis_weights[0])), 
					int(bool_to_value({k : i for k, i in o["i"].items() if k in self.pis_weights[1] }, self.pis_weights[1]))
				)
				: 
				int(bool_to_value(o["a"], self.po_weights)) for o in computed_circuit_outputs 
			}
		