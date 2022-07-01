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

import json
from pyAMOSA.AMOSA import *
from .ALSSMT import *
from .ErrorMetrics import *
from .HwMetrics import *


class ConfigParser:
	def __init__(self, config_file, command):
		configuration = json.load(open(config_file))
		self.source_hdl = ConfigParser.search_field_in_config(configuration, "hdl", "source", True)
		self.top_module = ConfigParser.search_field_in_config(configuration, "hdl", "top", True)
		self.output_dir = ConfigParser.search_field_in_config(configuration, "hdl", "output", True if command in ["als"] else False)
		self.lut_cache = ConfigParser.search_field_in_config(configuration, "als", "cache", True if command in ["als", "es"] else False)
		self.als_conf = ALSConfig(
			cut_size = str(ConfigParser.search_field_in_config(configuration, "als", "cut_size", True if command in ["als", "es"] else False)),
			solver = ConfigParser.search_field_in_config(configuration, "als", "solver", True if command in ["als", "es"] else False),
			timeout = int(ConfigParser.search_field_in_config(configuration, "als", "timeout", True if command in ["als", "es"] else False)))
		self.error_conf = None
		self.hw_conf = None
		self.amosa_conf = None
		if command == "als":
			self.error_conf = ErrorConfig(
				metric = ConfigParser.search_field_in_config(configuration, "error", "metric", True),
				threshold = float(ConfigParser.search_field_in_config(configuration, "error", "threshold", True)),
				vectors = int(ConfigParser.search_field_in_config(configuration, "error", "vectors", True)))
			self.error_conf.weights = ConfigParser.search_field_in_config(configuration, "error", "weights",  self.error_conf.builtin_metric and  self.error_conf.metric in [ErrorConfig.Metric.AWCE, ErrorConfig.Metric.MED])
			self.error_conf.dataset = ConfigParser.search_field_in_config(configuration, "error", "dataset", False)

			self.hw_conf = HwConfig(ConfigParser.search_field_in_config(configuration, "hardware", "metrics", True))
			self.amosa_conf = AMOSAConfig(
				archive_hard_limit = int(ConfigParser.search_field_in_config(configuration, "amosa", "archive_hard_limit", True)),
				archive_soft_limit = int(ConfigParser.search_field_in_config(configuration, "amosa", "archive_soft_limit", True)),
				archive_gamma = int(ConfigParser.search_field_in_config(configuration, "amosa", "archive_gamma", True)),
				clustering_max_iterations = int(ConfigParser.search_field_in_config(configuration, "amosa", "clustering_iterations", True)),
				hill_climbing_iterations = int(ConfigParser.search_field_in_config(configuration, "amosa", "hill_climbing_iterations", True)),
				initial_temperature = float(ConfigParser.search_field_in_config(configuration, "amosa", "initial_temperature", True)),
				final_temperature = float(ConfigParser.search_field_in_config(configuration, "amosa", "final_temperature", True)),
				cooling_factor = float(ConfigParser.search_field_in_config(configuration, "amosa", "cooling_factor", True)),
				annealing_iterations = int(ConfigParser.search_field_in_config(configuration, "amosa", "annealing_iterations", True)),
				annealing_strength = int(ConfigParser.search_field_in_config(configuration, "amosa", "annealing_strength", True)),
				early_termination_window = int(ConfigParser.search_field_in_config(configuration, "amosa", "early_termination", True)),
				multiprocessing_enabled = bool(ConfigParser.search_field_in_config(configuration, "amosa", "multiprocess_enabled", True)))

	@staticmethod
	def search_field_in_config(configuration, section, field, mandatory = False):
		try:
			return configuration[section][field]
		except KeyError as e:
			if mandatory:
				print(f"{e} not found in the configuration")
				exit()
			else:
				return None
