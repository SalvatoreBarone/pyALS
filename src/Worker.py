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
import os, sys, argparse, configparser
from pyosys import libyosys as ys
from distutils.dir_util import mkpath
from .ALSGraph import *
from .ALSCatalog import *
from .Error import *
from .AMOSA import *
from .ALSRewriter import *

class Worker:
    __report_file = "/pareto_front.csv"
    __pareto_view = "/pareto_front.pdf"

    def __init__(self):
        self.__cli_parser()
        self.__config_parser()

    def work(self):
        if self.__output_dir != ".":
            mkpath(self.__output_dir)
        design = ys.Design()
        ys.run_pass("plugin -i ghdl", design)
        self.__read_source(design)
        graph = ALSGraph(design)
        print(f"Performing catalog generation using {cpu_count()} threads. Please wait patiently. This may take time.")
        catalog = ALSCatalog(self.__als_conf.catalog, self.__als_conf.solver).generate_catalog(design, self.__als_conf.timeout)
        print(f"Performing AMOSA heuristic using {cpu_count()} threads. Please wait patiently. This may take time.")
        problem = None
        if self.__error_conf.metric == ErrorConfig.Metric.EPROB:
            problem = ErrorProbability(graph, catalog, self.__error_conf.n_vectors, self.__error_conf.threshold)
        elif self.__error_conf.metric == ErrorConfig.Metric.AWCE:
            self.__error_conf.weights = self.__parse_weights(graph)
            problem = AWCE(graph, catalog, self.__error_conf.n_vectors, self.__error_conf.threshold, self.__error_conf.weights)
        elif self.__error_conf.metric == ErrorConfig.Metric.MED:
            self.__error_conf.weights = self.__parse_weights(graph)
            problem = MED(graph, catalog, self.__error_conf.n_vectors, self.__error_conf.threshold, self.__error_conf.weights)

        optimizer = AMOSA(self.__amosa_conf)
        optimizer.minimize(problem)
        print(f"Took {optimizer.duration} sec.")
        optimizer.save_results(problem, self.__output_dir + self.__report_file)
        optimizer.plot_pareto(problem, self.__output_dir + self.__pareto_view)
        print(f"Performing AIG-rewriting.")
        rewriter = ALSRewriter(graph, catalog)
        pareto_set = optimizer.pareto_set()
        for c, n in zip(pareto_set, range(len(pareto_set))):
            rewriter.rewrite("original", c, self.__output_dir + "/variant_" + str(n))
        print(f"All done! Take a look at {self.__output_dir}!")

    def __cli_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", type=str, help="path of the configuration file", default="config.ini")
        parser.add_argument("--source", type=str, help="specify the input HDL source file")
        parser.add_argument("--weights", type=str, help="specify weights for AWCE evaluation")
        parser.add_argument("--top", type=str, help="specify the top-module name ")
        parser.add_argument("--output", type=str, help="Output directory. Everything will be placed there.", default="output/")
        args, left = parser.parse_known_args()
        sys.argv = sys.argv[:1] + left
        self.__config_file = args.config
        self.__source_file = args.source
        self.__weights_file = args.weights
        self.__top_module = args.top
        self.__output_dir = args.output

    def __config_parser(self):
        config = configparser.ConfigParser()
        config.read(self.__config_file)

        self.__als_conf = ALSConfig(
            config["als"]["cut_size"] if "cut_size" in config["als"] else "4",
            config["als"]["catalog"] if "catalog" in config["als"] else "lut_catalog.db",
            config["als"]["solver"] if "solver" in config["als"] else "boolector",
            int(config["als"]["timeout"]) if "timeout" in config["als"] else 60000)

        self.__error_conf = ErrorConfig(
            config["error"]["metric"] if "metric" in config["error"] else "ers",
            float(config["error"]["threshold"]) if "threshold" in config["error"] else .5,
            int(config["error"]["vectors"] if "vectors" in config["error"] else 1000))

        self.__amosa_conf = AMOSAConfig(
            int(config["amosa"]["archive_hard_limit"]) if "archive_hard_limit" in config["amosa"] else 50,
            int(config["amosa"]["archive_soft_limit"]) if "archive_soft_limit" in config["amosa"] else 100,
            int(config["amosa"]["archive_gamma"]) if "archive_gamma" in config["amosa"] else 3,
            int(config["amosa"]["hill_climbing_iterations"]) if "hill_climbing_iterations" in config["amosa"] else 100,
            float(config["amosa"]["initial_temperature"]) if "initial_temperature" in config["amosa"] else 500,
            float(config["amosa"]["final_temperature"]) if "final_temperature" in config["amosa"] else 0.0000001,
            float(config["amosa"]["cooling_factor"]) if "cooling_factor" in config["amosa"] else 0.8,
            int(config["amosa"]["annealing_iterations"]) if "annealing_iterations" in config["amosa"] else 100)

    def __parse_weights(self, graph):
        with open(self.__weights_file, "r") as weights_file:
            raw_data = weights_file.readlines()
        raw_data = "".join(raw_data)
        weights = eval(raw_data)
        po_names = [o["name"] for o in graph.get_po()]
        for k in weights.keys():
            if k not in po_names:
                graph.plot()
                raise ValueError(f"{k} not found in POs {po_names}")
        return weights

    def __read_source(self, design):
        name, extension = os.path.splitext(self.__source_file)
        if extension == ".vhd":
            ys.run_pass(f"ghdl {self.__source_file} -e {self.__top_module}", design)
        elif extension == ".sv":
            ys.run_pass(f"read_verilog -sv {self.__source_file}", design)
        elif extension == ".v":
            ys.run_pass(f"read_verilog {self.__source_file}", design)
        elif extension == ".blif":
            ys.run_pass(f"read_blif {self.__source_file}", design)
        ys.run_pass(f"hierarchy -check -top {self.__top_module}; prep; flatten; splitnets -ports; synth -top {self.__top_module}; flatten; clean -purge; synth -lut {str(self.__als_conf.luttech)}", design)
        ys.run_pass("design -save original", design)