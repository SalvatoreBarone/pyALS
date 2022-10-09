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
import os, json
from .ALSGraph import *
from .YosysHelper import *
from .ErrorMetrics import *
from distutils.dir_util import mkpath
from distutils.file_util import copy_file
from .template_render import template_render


class ALSArithModelDescription:
	def __init__(self, config_file):
		with open(config_file) as f:
			configuration = json.load(f)
		self.operand1 = {
			"name" : ALSArithModelDescription.search_subfield_in_config(configuration, "operand1", "name"),
			"width" : ALSArithModelDescription.search_subfield_in_config(configuration, "operand1", "width"),
			"weights" : ALSArithModelDescription.search_subfield_in_config(configuration, "operand1", "weights")
		}
		self.operand2 = {
			"name" : ALSArithModelDescription.search_subfield_in_config(configuration, "operand2", "name"),
			"width" : ALSArithModelDescription.search_subfield_in_config(configuration, "operand2", "width"),
			"weights" : ALSArithModelDescription.search_subfield_in_config(configuration, "operand2", "weights")
		}
		self.result = {
			"name" : ALSArithModelDescription.search_subfield_in_config(configuration, "result", "name"),
			"width" : ALSArithModelDescription.search_subfield_in_config(configuration, "result", "width"),
			"weights" : ALSArithModelDescription.search_subfield_in_config(configuration, "result", "weights")
		}

	@staticmethod
	def search_field_in_config(configuration, field, mandatory = True, default_value = None):
		try:
			return configuration[field]
		except KeyError as e:
			if mandatory:
				print(f"{e} not found in the configuration")
				exit()
			else:
				return default_value


	@staticmethod
	def search_subfield_in_config(configuration, section, field, mandatory = True, default_value = None):
		try:
			return configuration[section][field]
		except KeyError as e:
			if mandatory:
				print(f"{e} not found in the configuration")
				exit()
			else:
				return default_value

class ALSArithModel:
	__resource_dir = "../resources/"
	__lut_mode_py = "lut_model.py.template"

	def __init__(self, helper, problem, model_description_file, design_name = "original"):
		dir_path = os.path.dirname(os.path.abspath(__file__))
		self.resource_dir =  f"{dir_path}/{self.__resource_dir}"
		self.lut_mode_py = f"{self.resource_dir}{self.__lut_mode_py}"

		self.helper = helper
		self.problem = problem
		self.description = ALSArithModelDescription(model_description_file)
		self.design_name = design_name
		self.helper.load_design(design_name)
		self.helper.reverse_splitnets()
		wires = helper.get_PIs_and_Pos()
	
	def get_lookup_table_models(self, top_module, pareto_set, destination):
		items = {
			"top_module" : top_module,
			"operand1" : self.description.operand1["name"],
			"operand2" : self.description.operand2["name"],
			"variants" : []
		}
		for c, n in zip(pareto_set, range(len(pareto_set))):
			configuration = self.problem.matter_configuration(c)
			outputs = self.problem.get_outputs(configuration)
			function_name = f"variant_{n:05d}"
			model = self.generate_lookup_table(outputs)
			items["variants"].append((function_name, model))
		template_render(self.resource_dir, self.__lut_mode_py, items, destination)
		

	def get_regression_models(self, pareto_set, output_directory):
		for c, n in zip(pareto_set, range(len(pareto_set))):
			self.regression(c, f"{output_directory}/variant_{n:05d}.py")

	def regression(self, solution, destination):
		print(f"Generating {destination}")
		pass

	def generate_lookup_table(self, outputs):
		return {(bool_to_value({k : i for k, i in o["i"].items() if k in self.description.operand1["weights"] }, self.description.operand1["weights"]), bool_to_value({k : i for k, i in o["i"].items() if k in self.description.operand2["weights"] }, self.description.operand2["weights"])) : bool_to_value(o["a"], self.description.result["weights"]) for o in outputs }
		