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
		
	def __init__(self, config_file):
		configuration = json.load(open(config_file))

		self.source_hdl = ConfigParser.search_subfield_in_config(configuration, "circuit", "sources", True)
		self.top_module = ConfigParser.search_subfield_in_config(configuration, "circuit", "top_module", True)
		self.output_dir = ConfigParser.search_field_in_config(configuration, "output_path", True)
		self.lut_cache = ConfigParser.search_subfield_in_config(configuration, "als", "cache", True)
		self.als_conf = ALSConfig(
			cut_size = str(ConfigParser.search_subfield_in_config(configuration, "als", "cut_size", True)),
			solver = ConfigParser.search_subfield_in_config(configuration, "als", "solver", True),
			timeout = int(ConfigParser.search_subfield_in_config(configuration, "als", "timeout", True)))

		self.error_conf = ErrorConfig(
				metrics = ConfigParser.search_subfield_in_config(configuration, "error", "metrics", True),
				thresholds = ConfigParser.search_subfield_in_config(configuration, "error", "threshold", True),
				n_vectors = int(ConfigParser.search_subfield_in_config(configuration, "error", "vectors", True)),
				dataset = ConfigParser.search_subfield_in_config(configuration, "error", "dataset", False))

		self.weights = ConfigParser.search_subfield_in_config(configuration, "circuit", "io_weights", self.error_conf.builtin_metric and self.error_conf.metrics in [ErrorConfig.Metric.AWCE, ErrorConfig.Metric.MED])
		
		self.hw_conf = HwConfig(ConfigParser.search_subfield_in_config(configuration, "hardware", "metrics", True))

		self.amosa_conf = AMOSAConfig(
				archive_hard_limit = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "archive_hard_limit", True)),
				archive_soft_limit = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "archive_soft_limit", True)),
				archive_gamma = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "archive_gamma", True)),
				clustering_max_iterations = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "clustering_iterations", True)),
				hill_climbing_iterations = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "hill_climbing_iterations", True)),
				initial_temperature = float(ConfigParser.search_subfield_in_config(configuration, "amosa", "initial_temperature", True)),
				final_temperature = float(ConfigParser.search_subfield_in_config(configuration, "amosa", "final_temperature", True)),
				cooling_factor = float(ConfigParser.search_subfield_in_config(configuration, "amosa", "cooling_factor", True)),
				annealing_iterations = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "annealing_iterations", True)),
				annealing_strength = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "annealing_strength", True)),
				early_termination_window = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "early_termination", True)),
				multiprocessing_enabled = bool(ConfigParser.search_subfield_in_config(configuration, "amosa", "multiprocess_enabled", True)))

	@staticmethod
	def search_field_in_config(configuration, field, mandatory = True, default_value = None):
		try:
			return configuration[field]
		except KeyError as e:
			if not mandatory:
				return default_value
			print(f"{e} not found in the configuration. Please see the README.md file for details concerning the configuration file")
			exit()


	@staticmethod
	def search_subfield_in_config(configuration, section, field, mandatory = True, default_value = None):
		try:
			return configuration[section][field]
		except KeyError as e:
			if not mandatory:
				return default_value
			print(f"{e} not found in the configuration. Please see the README.md file for details concerning the configuration file")
			exit()
