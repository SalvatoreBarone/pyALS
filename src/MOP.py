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
import itertools, pyamosa, numpy as np, copy
from pyalslib import list_partitioning, negate, flatten
from multiprocessing import cpu_count, Pool
from .HwMetrics import *
from .ErrorMetrics import *
from tqdm import tqdm

class MOP(pyamosa.Problem):
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
        self.samples = None
        self.n_vectors = 0
        lut_io_info = self.generate_samples()
        self.ncpus = ncpus
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

    # def load_dataset(self):
    #     print(f"Reading input data from {self.error_config.dataset} ...")
    #     if self.error_config.dataset.endswith(".json5"):
    #         self.samples = json5.load(open(self.error_config.dataset))
    #         lut_io_info = {}
    #         for s in self.samples:
    #             _, lut_io_info = self.graph.evaluate(s["input"], lut_io_info)
    #         return lut_io_info
    #     print("Done!")
    #     return self.read_samples(self.error_config.dataset)

    # def store_dataset(self, dataset_outfile):
    #     if dataset_outfile is not None:
    #         if not dataset_outfile.endswith(".json5"):
    #             dataset_outfile += ".json5"
    #         print(f"Storing generated random vectors on {dataset_outfile} further use...")
    #         with open(dataset_outfile, 'w') as outfile:
    #             outfile.write(json5.dumps(self.samples))

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

    # def read_samples(self, dataset):
    #     self.samples = []
    #     PI = self.graph.get_pi()
    #     file = open(dataset, "r")
    #     header = list(filter(None, file.readline().replace("\n", "").split(",")))
    #     assert len(header) == len(PI), f"{dataset}: wrong amount of inputs (header: {len(header)} PI: {len(PI)})"
    #     input_dict = {h : [] for h in header}
    #     for row in file:
    #         input_values = list(filter(None, row.replace("\n", "").split(",")))
    #         assert len(input_values) == len(PI), f"{dataset}: wrong amount of inputs"
    #         for i, v in zip(input_values, input_dict.values()):
    #             v.append(i)
    #     lut_io_info = {}
    #     for i in range(len(list(input_dict.values())[0])):
    #         inputs = {k["name"]: input_dict[k["name"]][i] == '1' for k in PI}
    #         output, lut_io_info = self.graph.evaluate(inputs, lut_io_info)
    #         self.samples.append({"input": inputs, "output": output})
    #     return lut_io_info

    def generate_samples(self):
        self.samples = []
        PI = self.graph.get_pi()
        lut_io_info = {}
        self.n_vectors = 2 ** len(PI)
        permutations = [list(i) for i in itertools.product([False, True], repeat = len(PI))]
        for perm in tqdm(permutations, desc = "Generating input-vectors...", bar_format="{desc:40} {percentage:3.0f}% |{bar:60}{r_bar}{bar:-10b}"):
            inputs = {i["name"]: p for i, p in zip(PI, perm)}
            output, lut_io_info = self.graph.evaluate(inputs, lut_io_info)
            self.samples.append({"input": inputs, "output": output})
        print("Done!")
        return lut_io_info

    def matter_configuration(self, x):
        matter = {}
        for i, (c, l) in enumerate(zip(x, self.graph.get_cells())):
            for e in self.catalog:
                try:
                    if e[0]["spec"] == l["spec"]:
                        matter[l["name"]] = {
                            "dist": c, 
                            "spec": e[0]["spec"],
                            "axspec": e[c]["spec"],
                            "gates": e[c]["gates"],
                            "S": e[c]["S"],
                            "P": e[c]["P"],
                            "out_p": e[c]["out_p"],
                            "out": e[c]["out"],
                            "depth": e[c]["depth"]}
                    if negate(e[0]["spec"]) == l["spec"]:
                        matter[l["name"]] = {
                            "dist": c,
                            "spec": negate(e[0]["spec"]),
                            "axspec": negate(e[c]["spec"]),
                            "gates": e[c]["gates"],
                            "S": e[c]["S"],
                            "P": e[c]["P"],
                            "out_p": 1 - e[c]["out_p"],
                            "out": e[c]["out"],
                            "depth": e[c]["depth"]}
                except IndexError as err:
                    print(err)
                    print(f"Configuration: {x}")
                    print(f"Upper bound: {self.upper_bound}")
                    print(f"Configuration[{i}]: {c}")
                    print(f"Upper bound[{i}]: {self.upper_bound[i]}")
                    print(f"Cell: {l}")
                    print(f"Catalog Entries #: {len(e)}")
                    print(f"Catalog Entries: {e}")
                    exit()
        return matter

    def plot_labels(self):
        error_labels = {
            ErrorConfig.Metric.EPROB: "Error probability",
            ErrorConfig.Metric.AWCE: "AWCE",
            ErrorConfig.Metric.MAE: "MAE",
            ErrorConfig.Metric.WRE: "WRE",
            ErrorConfig.Metric.MRE: "MRE",
            ErrorConfig.Metric.MSE: "MSE",
            ErrorConfig.Metric.MED: "MED",
            ErrorConfig.Metric.ME: "ME",
            ErrorConfig.Metric.MRED: "MRED",
            ErrorConfig.Metric.RMSED: "RMSED",
            ErrorConfig.Metric.VARED: "VarED"
        }
        hw_labels = {
            HwConfig.Metric.GATES: "#AIG nodes",
            HwConfig.Metric.DEPTH: "AIG depth",
            HwConfig.Metric.SWITCHING: "Switching activity"
        }
        return [error_labels[m] for m in self.error_config.metrics] + [hw_labels[m] for m in self.hw_config.metrics] if self.error_config.builtin_metric else ["Error"] + [hw_labels[m] for m in self.hw_config.metrics]

    def get_upper_bound(self):
        return [len(e) - 1 for c in [{"name": c["name"], "spec": c["spec"]} for c in self.graph.get_cells()] for e in self.catalog if e[0]["spec"] == c["spec"] or negate(e[0]["spec"]) == c["spec"] ]

    @staticmethod
    def evaluate_output(graph, samples, configuration):
        lut_io_info = {}
        outputs = []
        for s in samples:
            ax_output, lut_io_info = graph.evaluate(s["input"], lut_io_info, configuration)
            outputs.append({"i" : s["input"], "e" : s["output"], "a" : ax_output })
        return outputs, lut_io_info

    def get_outputs(self, configuration):
        for a in self._args:
            a[2] = configuration
        with Pool(self.ncpus) as pool:
           outputs = pool.starmap(MOP.evaluate_output, self._args)
        out = [o[0] for o in outputs]
        swc = [o[1] for o in outputs]
        lut_io_info = {}
        for k in swc[0].keys():
            C = [s[k]["freq"] for s in swc if k in s.keys()]
            lut_io_info[k] = { "spec": swc[0][k]["spec"], "freq" : [sum(x) for x in zip(*C)]}
        return list(flatten(out)), lut_io_info

    def get_baseline_gates(self, lut_io_info):
        return get_gates(self.matter_configuration([0] * self.n_vars), lut_io_info, self.graph)

    def get_baseline_depth(self, lut_io_info):
        return get_depth(self.matter_configuration([0] * self.n_vars), lut_io_info, self.graph)

    def get_baseline_switching(self, lut_io_info):
        return get_switching(self.matter_configuration([0] * self.n_vars), lut_io_info, self.graph)

    def get_ep(self, outputs, weights):
        rs = sum(o["e"] != o["a"] for o in outputs) / len(outputs)
        if self.n_vectors != 0:
            return float(np.min([1.0, rs + 4.5 / self.n_vectors * (1 + np.sqrt(1 + 4 / 9 * self.n_vectors * rs * (1 - rs)))]))
        else:
            return float(rs)
        
    @staticmethod
    def evaluate_abs_ed(outputs, weights):
        return [np.abs( bool_to_value(o["e"], weights) - bool_to_value(o["a"], weights) ) for o in outputs] if weights is not None else [0]

    @staticmethod
    def evaluate_signed_ed(outputs, weights):
        return [bool_to_value(o["a"], weights) - bool_to_value(o["e"], weights) for o in outputs] if weights is not None else [0] 

    @staticmethod
    def evaluate_squared_ed(outputs, weights):
        return [( bool_to_value(o["e"], weights) - bool_to_value(o["a"], weights))**2 for o in outputs] if weights is not None else [0]

    @staticmethod
    def evaluate_relative_ed(outputs, weights):
        if weights is None:
            return [0]
        err = []
        for o in outputs:
            f =  float(bool_to_value(o["e"], weights))
            axf = float(bool_to_value(o["a"], weights))
            err.append(np.abs(f - axf) / (1 if np.abs(f) <= np.finfo(float).eps else f))
        return err

    def get_awce(self, outputs, weights):
        return np.max(MOP.evaluate_abs_ed(outputs, weights))

    def get_mae(self, outputs, weights):
        return np.mean(MOP.evaluate_abs_ed(outputs, weights))

    def get_mre(self, outputs, weights):
        return np.mean(MOP.evaluate_relative_ed(outputs, weights))

    def get_wre(self, outputs, weights):
        return np.max(MOP.evaluate_relative_ed(outputs, weights))

    def get_mse(self, outputs, weights):
        return np.mean(MOP.evaluate_squared_ed(outputs, weights))

    @staticmethod
    def get_error_hystogram(error, decimals = 2):
        error_hystogram = {}
        for e in error:
            index = round(e, decimals)
            if index in error_hystogram:
                error_hystogram[index] += 1
            else:
                error_hystogram[index] = 1
        return error_hystogram
           
    @staticmethod     
    def get_mxxd(hystogram):
        return np.sum([k * v for k, v in hystogram.items()]) / np.sum(list(hystogram.values()))

    def get_med(self, outputs, weights):
        return MOP.get_mxxd(MOP.get_error_hystogram(MOP.evaluate_abs_ed(outputs, weights)))
    
    def get_me(self, outputs, weights):
        return MOP.get_mxxd(MOP.get_error_hystogram(MOP.evaluate_signed_ed(outputs, weights)))

    def get_mred(self, outputs, weights):
        return MOP.get_mxxd(MOP.get_error_hystogram(MOP.evaluate_relative_ed(outputs, weights)))

    def get_rmsed(self, outputs, weights):
        return np.sqrt(np.mean(MOP.evaluate_squared_ed(outputs, weights)))

    def get_vared(self, outputs, weights):
        return np.var(MOP.evaluate_signed_ed(outputs, weights))
