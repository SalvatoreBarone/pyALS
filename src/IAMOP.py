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
import itertools, pyamosa, numpy as np, copy, json5
from pyalslib import list_partitioning, negate, flatten
from multiprocessing import cpu_count, Pool
from .HwMetrics import *
from .ErrorMetrics import *
from tqdm import tqdm
from .MOP import MOP

class IAMOP(MOP):
    error_ffs = {
        ErrorConfig.Metric.EPROB : "get_ep",
        ErrorConfig.Metric.AWCE  : "get_awce",
        ErrorConfig.Metric.MAE   : "get_mae",
        ErrorConfig.Metric.WRE   : "get_wre",
        ErrorConfig.Metric.MRE   : "get_mre",
        ErrorConfig.Metric.MSE   : "get_mse",
        ErrorConfig.Metric.MED   : "get_med",
        ErrorConfig.Metric.ME    : "get_me",
        ErrorConfig.Metric.MRED  : "get_mred",
        ErrorConfig.Metric.RMSED : "get_rmsed",
        ErrorConfig.Metric.VARED : "get_vared"
    }
    hw_ffs = {
        HwConfig.Metric.GATES:      get_gates,
        HwConfig.Metric.DEPTH:      get_depth,
        HwConfig.Metric.SWITCHING:  get_switching
    }
    
    def __init__(self, top_module, graph, output_weights, catalog, error_config, hw_config, ncpus):
        self.top_module = top_module
        self.graph = graph
        self.output_weights = output_weights
        self.graphs = [copy.deepcopy(graph) for _ in range(cpu_count())]
        self.n_vars = graph.get_num_cells()
        self.catalog = catalog
        self.error_config = error_config
        self.hw_config = hw_config
        self.ncpus = ncpus
        self.samples = None
        self.n_vectors = 0
        #TODO read the samples from json/json5 file, besides their probabilities, for input-aware error measurement
        #The "read_sample" must generate lut_io_info for switching activity estimation
        
        
        self._args = [[g, s, [0] * self.n_vars] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))] if self.error_config.builtin_metric else None
        self.upper_bound = self.get_upper_bound()
        self.baseline_and_gates = self.get_baseline_gates(None)
        self.baseline_depth = self.get_baseline_depth(None)
        self.baseline_switching = self.get_baseline_switching(lut_io_info)
        print("Optimized error metrics:")
        for m, t in zip(self.error_config.metrics, self.error_config.thresholds):
            print(f"\t - {m} with threshold {t}")
        print("Optimized resources metrics:")
        for m in self.hw_config.metrics:
            print(f"\t - {m}")
        print(f"#vars: {self.n_vars}, ub:{self.upper_bound}, #conf.s {np.prod([ float(x + 1) for x in self.upper_bound ])}.")
        print(f"Baseline requirements. Nodes: {self.baseline_and_gates}. Depth: {self.baseline_depth}. Switching: {self.baseline_switching}")
        pyamosa.Problem.__init__(self, self.n_vars, [pyamosa.Type.INTEGER] * self.n_vars, [0] * self.n_vars, self.upper_bound, len(self.error_config.metrics) + len(self.hw_config.metrics), len(self.error_config.metrics))
        
    def evaluate(self, x, out):
        out["f"] = []
        out["g"] = []
        configuration = self.matter_configuration(x)
        
        outputs, lut_io_info = self.get_outputs(configuration)    
        for m, t in zip(self.error_config.metrics, self.error_config.thresholds):
            out["f"].append(getattr(self, self.error_ffs[m])(outputs, self.output_weights))
            out["g"].append(out["f"][-1] - t)
        for metric in self.hw_config.metrics:
            out["f"].append(self.hw_ffs[metric](configuration, lut_io_info, self.graph))

    def evaluate_ffs(self, x):
        out = { "f" : [], "g": []}
        configuration = self.matter_configuration(x)
        outputs, lut_io_info = self.get_outputs(configuration)
        for m in self.error_config.metrics:
            out["f"].append(getattr(self, self.error_ffs[m])(outputs, self.output_weights))
        for metric in self.hw_config.metrics:
            out["f"].append(self.hw_ffs[metric](configuration, lut_io_info, self.graph))
        return out
