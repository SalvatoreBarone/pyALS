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
import sys, os, itertools, collections, functools, operator, json
from multiprocessing import cpu_count, Pool
import numpy as np

from .HwMetrics import *
from .ErrorMetrics import *
from .ALSGraph import *
from .Utility import *
from .ALSRewriter import *
from pyAMOSA.AMOSA import *


class MOP(AMOSA.Problem):
    error_ffs = {
        ErrorConfig.Metric.EPROB : "get_ep",
        ErrorConfig.Metric.AWCE  : "get_awce",
        ErrorConfig.Metric.MAE   : "get_mae",
        ErrorConfig.Metric.WRE   : "get_wre",
        ErrorConfig.Metric.MRE   : "get_mre",
        ErrorConfig.Metric.MSE   : "get_mse",
        ErrorConfig.Metric.MED   : "get_med",
        ErrorConfig.Metric.MRED  : "get_mred",
        ErrorConfig.Metric.RMSED : "get_rmsed",
        ErrorConfig.Metric.VARED : "get_vared"
    }
    hw_ffs = {
        HwConfig.Metric.GATES:      get_gates,
        HwConfig.Metric.DEPTH:      get_depth,
        HwConfig.Metric.SWITCHING:  get_switching
    }

    def __init__(self, top_module, graph, catalog, error_config, hw_config, dataset_outfile):
        self.top_module = top_module
        self.graph = graph
        self.graphs = [copy.deepcopy(graph)] * cpu_count()
        self.n_vars = graph.get_num_cells()
        self.catalog = catalog
        self.error_config = error_config
        self.hw_config = hw_config
        self.samples = None
        if self.error_config.dataset is None:
            self._generate_samples()
            self._store_dataset(dataset_outfile)
        else:
            self._load_dataset()
        print("Done!")
        self._args = [[g, s, [0] * self.n_vars, self.error_config.weights] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))] if self.error_config.builtin_metric else None
        self.upper_bound = self._get_upper_bound()
        self.baseline_and_gates = self._get_baseline_gates()
        self.baseline_depth = self._get_baseline_depth()
        self.baseline_switching = self._get_baseline_switching()
        print(f"#vars: {self.n_vars}, ub:{self.upper_bound}, #conf.s {np.prod([ float(x + 1) for x in self.upper_bound ])}.")
        print(f"Baseline requirements. Nodes: {self.baseline_and_gates}. Depth: {self.baseline_depth}. Switching: {self.baseline_switching}")
        AMOSA.Problem.__init__(self, self.n_vars, [AMOSA.Type.INTEGER] * self.n_vars, [0] * self.n_vars, self.upper_bound, len(self.hw_config.metrics) + 1, 1)

    def _load_dataset(self):
        print(f"Reading input data from {self.error_config.dataset} ...")
        if self.error_config.dataset.endswith(".json"):
            self.samples = json.load(open(self.error_config.dataset))
        else:
            self._read_samples(self.error_config.dataset)

    def _store_dataset(self, dataset_outfile):
        if dataset_outfile is not None:
            if not dataset_outfile.endswith(".json"):
                dataset_outfile += ".json"
            print(f"Storing generated random vectors on {dataset_outfile} further use...")
            with open(dataset_outfile, 'w') as outfile:
                outfile.write(json.dumps(self.samples))

    def evaluate(self, x, out):
        out["f"] = []
        out["g"] = []
        configuration = self._matter_configuration(x)
        if self.error_config.builtin_metric:
            out["f"].append(getattr(self, self.error_ffs[self.error_config.metric])(configuration))
        else:
            out["f"].append(self.error_config.function(self.graph, self.samples, configuration, self.error_config.weights))
        out["g"].append(out["f"][-1] - self.error_config.threshold)
        for metric in self.hw_config.metrics:
            out["f"].append(self.hw_ffs[metric](configuration))

    def _read_samples(self, dataset):
        self.samples = []
        PI = self.graph.get_pi()
        file = open(dataset, "r")
        header = list(filter(None, file.readline().replace("\n", "").split(",")))
        assert len(header) == len(PI), f"{dataset}: wrong amount of inputs (header: {len(header)} PI: {len(PI)})"
        input_dict = {h : [] for h in header}
        for row in file:
            input_values = list(filter(None, row.replace("\n", "").split(",")))
            assert len(input_values) == len(PI), f"{dataset}: wrong amount of inputs"
            for i, v in zip(input_values, input_dict.values()):
                v.append(i)
        for i in range(len(list(input_dict.values())[0])):
            inputs = { k["name"] :  True if input_dict[k["name"]][i] == '1' else False for k in PI }
            self.samples.append({"input": inputs, "output": self.graph.evaluate(inputs)})

    def _generate_samples(self):
        self.samples = []
        PI = self.graph.get_pi()
        if self.error_config.n_vectors != 0:
            print(f"Generating {self.error_config.n_vectors} input-vectors for error assessment...")
            for _ in range(self.error_config.n_vectors):
                inputs = {i["name"]: bool(random.getrandbits(1)) for i in PI}
                self.samples.append({"input": inputs, "output": self.graph.evaluate(inputs)})
        else:
            self.error_config.n_vectors = 2 ** len(PI)
            print(f"Generating {self.error_config.n_vectors} input-vectors for error assessment...")
            permutations = [list(i) for i in itertools.product([False, True], repeat = len(PI))]
            for perm in permutations:
                inputs = {i["name"]: p for i, p in zip(PI, perm)}
                self.samples.append({"input": inputs, "output": self.graph.evaluate(inputs)})

    def _matter_configuration(self, x):
        # first, prevent x to be out of range
        x = list(np.minimum(np.maximum(np.array([0] * self.n_vars), np.array(x)), np.array(self.upper_bound)))        # then, get the corresponding matter configuration
        matter = {}
        for c, l in zip(x, self.graph.get_cells()):
            for e in self.catalog:
                if e[0]["spec"] == l["spec"]:
                    matter[l["name"]] = {"dist": c, "spec": e[0]["spec"], "axspec": e[c]["spec"], "gates": e[c]["gates"], "S": e[c]["S"], "P": e[c]["P"], "out_p": e[c]["out_p"], "out": e[c]["out"], "depth": e[c]["depth"]}
                if negate(e[0]["spec"]) == l["spec"]:
                    matter[l["name"]] = {"dist": c, "spec": negate(e[0]["spec"]), "axspec": negate(e[c]["spec"]), "gates": e[c]["gates"], "S": e[c]["S"], "P": e[c]["P"], "out_p": 1 - e[c]["out_p"], "out": e[c]["out"], "depth": e[c]["depth"]}
        return matter

    def _get_upper_bound(self):
        return [len(e) - 1 for c in [{"name": c["name"], "spec": c["spec"]} for c in self.graph.get_cells()] for e in self.catalog if e[0]["spec"] == c["spec"] or negate(e[0]["spec"]) == c["spec"] ]

    def _get_outputs(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            outputs = pool.starmap(evaluate_output, self._args)
        return [ o for output in outputs for o in output ]

    def _get_baseline_gates(self):
        return get_gates(self._matter_configuration([0] * self.n_vars))

    def _get_baseline_depth(self):
        return get_depth(self._matter_configuration([0] * self.n_vars,), self.graph)

    def _get_baseline_switching(self):
        return get_switching(self._matter_configuration([0] * self.n_vars))

    def get_ep(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_ep, self._args)
        rs = np.sum(error) / self.error_config.n_vectors
        if self.error_config.n_vectors != 0:
            return float(np.min([1.0, rs + 4.5 / self.error_config.n_vectors * (1 + np.sqrt(1 + 4 / 9 * self.error_config.n_vectors * rs * (1 - rs)))]))
        else:
            return float(rs)

    def get_awce(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_absolute_ed, self._args)
        return float(np.max(np.concatenate(error).flat))

    def get_mae(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_absolute_ed, self._args)
        return float(np.average(np.concatenate(error).flat))

    def get_mre(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_relative_ed, self._args)
        return float(np.average(np.concatenate(error).flat))

    def get_wre(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_relative_ed, self._args)
        return float(np.max(np.concatenate(error).flat))

    def get_mse(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_squared_ed, self._args)
        return float(np.average(np.concatenate(error).flat))

    def get_med(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            hystogram = pool.starmap(evaluate_med, self._args)
        final_fistogram = {}
        total = 0
        for h in hystogram:
            for k, v in h.items():
                total += v
                if k in final_fistogram.keys():
                    final_fistogram[k] += v
                else:
                    final_fistogram[k] = v
        return float(np.sum([ k * v / total for k, v in final_fistogram.items()]))

    def get_mred(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            hystogram = pool.starmap(evaluate_mred, self._args)
        final_fistogram = {}
        total = 0
        for h in hystogram:
            for k, v in h.items():
                total += v
                if k in final_fistogram.keys():
                    final_fistogram[k] += v
                else:
                    final_fistogram[k] = v
        return float(np.sum([k * v / total for k, v in final_fistogram.items()]))

    def get_rmsed(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_squared_ed, self._args)
        return float(np.sqrt(np.average(np.concatenate(error).flat)))

    def get_vared(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_squared_ed, self._args)
        return float(np.var(np.concatenate(error).flat))