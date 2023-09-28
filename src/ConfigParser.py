"""
Copyright 2021-2023 Salvatore Barone <salvatore.barone@unina.it>

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

import json5, pyamosa
from pyalslib import ALSConfig
from .ErrorMetrics import *
from .HwMetrics import *

class ConfigParser:
    tso_selector = {"all" : pyamosa.VariableGrouping.TSObjective.All, "any": pyamosa.VariableGrouping.TSObjective.Any}
    tsv_selector = {"all" : pyamosa.VariableGrouping.TSVariable.All, "any" : pyamosa.VariableGrouping.TSVariable.Any}
        
    def __init__(self, config_file):
        configuration = json5.load(open(config_file))

        self.source_hdl = ConfigParser.search_subfield_in_config(configuration, "circuit", "sources", True)
        self.top_module = ConfigParser.search_subfield_in_config(configuration, "circuit", "top_module", True)
        self.output_dir = ConfigParser.search_field_in_config(configuration, "output_path", True)
        
        self.als_conf = ALSConfig(
            lut_cache = ConfigParser.search_subfield_in_config(configuration, "als", "cache", True),
            cut_size = str(ConfigParser.search_subfield_in_config(configuration, "als", "cut_size", True)),
            solver = ConfigParser.search_subfield_in_config(configuration, "als", "solver", True),
            timeout = int(ConfigParser.search_subfield_in_config(configuration, "als", "timeout", True)))

        self.error_conf = ErrorConfig(
                metrics = ConfigParser.search_subfield_in_config(configuration, "error", "metrics", True),
                thresholds = ConfigParser.search_subfield_in_config(configuration, "error", "thresholds", True))

        self.weights = ConfigParser.search_subfield_in_config(configuration, "circuit", "io_weights", self.error_conf.builtin_metric and self.error_conf.metrics not in [ErrorConfig.Metric.EPROB])
        
        self.hw_conf = HwConfig(ConfigParser.search_subfield_in_config(configuration, "hardware", "metrics", True))

        self.amosa_conf = pyamosa.Config(
                archive_hard_limit = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "archive_hard_limit", True)),
                archive_soft_limit = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "archive_soft_limit", True)),
                archive_gamma = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "archive_gamma", True)),
                clustering_max_iterations = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "clustering_iterations", True)),
                hill_climbing_iterations = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "hill_climbing_iterations", True)),
                initial_temperature = float(ConfigParser.search_subfield_in_config(configuration, "amosa", "initial_temperature", True)),
                cooling_factor = float(ConfigParser.search_subfield_in_config(configuration, "amosa", "cooling_factor", True)),
                annealing_iterations = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "annealing_iterations", True)),
                annealing_strength = int(ConfigParser.search_subfield_in_config(configuration, "amosa", "annealing_strength", True)),
                hill_climb_checkpoint_file = f"{self.output_dir}/hill_climb_checkpoint.json",
                minimize_checkpoint_file = f"{self.output_dir}/annealing_checkpoint.json",
                cache_dir = f"{self.output_dir}/.cache")
        
        self.variable_grouping_strategy = ConfigParser.search_subfield_in_config(configuration, "amosa", "grouping", False, None)
        self.transfer_strategy_objectives = ConfigParser.search_subfield_in_config(configuration, "amosa", "tso", False, "all")
        self.transfer_strategy_variables = ConfigParser.search_subfield_in_config(configuration, "amosa", "tsv", False, "any")
        
        optimizer_min_temperature = ConfigParser.search_subfield_in_config(configuration, "amosa", "final_temperature", False, 1e-7)
        optimizer_stop_phy_window = ConfigParser.search_subfield_in_config(configuration, "amosa", "early_termination", False, None)
        optimizer_max_duration =    ConfigParser.search_subfield_in_config(configuration, "amosa", "max_duration", False, None)
        self.termination_criterion = pyamosa.CombinedStopCriterion(optimizer_max_duration, optimizer_min_temperature, optimizer_stop_phy_window)

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
