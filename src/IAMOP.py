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
        ErrorConfig.Metric.MAE   : "get_mae",
        ErrorConfig.Metric.MRE   : "get_mre",
        ErrorConfig.Metric.MARE  : "get_mare",
        ErrorConfig.Metric.MSE   : "get_mse"
    }
    hw_ffs = {
        HwConfig.Metric.GATES:      get_gates,
        HwConfig.Metric.DEPTH:      get_depth,
        HwConfig.Metric.SWITCHING:  get_switching
    }
    
    def __init__(self, top_module, graph, output_weights, catalog, error_config, hw_config, dataset, ncpus):
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
        lut_io_info = self.load_dataset(dataset)
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
        
    def load_dataset(self, dataset):
        print(f"Reading input data from {dataset} ...")
        self.samples = json5.load(open(dataset))
        PIs = set(pi["name"] for pi in self.graph.get_pi())
        lut_io_info = {}
        self.error_config.n_vectors = len(self.samples)
        self.samples = []
        for sample in tqdm(self.samples, desc = "Checking input-vectors...", bar_format="{desc:40} {percentage:3.0f}% |{bar:60}{r_bar}{bar:-10b}"):
            assert PIs == set(sample["input"].keys())
            output, lut_io_info = self.graph.evaluate(sample["input"], lut_io_info)
            assert sample["output"] == output, f"\n\nRead output:\n{sample['output']}\n\nComputed output:\n{output}\n"
        return lut_io_info

    