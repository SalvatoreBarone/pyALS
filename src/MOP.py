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
import random, itertools, collections, functools, operator, gc
from multiprocessing import cpu_count, Pool
from liberty.parser import parse_liberty
from enum import Enum
from .AMOSA import *
from .ALSGraph import *
from .Utility import *
from .ALSRewriter import *

class ErrorConfig:
    class Metric(Enum):
        EPROB = 1
        AWCE = 2
        MED = 3

    def __init__(self, metric, threshold, vectors, weights = None):
        error_metrics = {
            "eprob": ErrorConfig.Metric.EPROB,
            "EProb": ErrorConfig.Metric.EPROB,
            "EPROB": ErrorConfig.Metric.EPROB,
            "awce": ErrorConfig.Metric.AWCE,
            "AWCE": ErrorConfig.Metric.AWCE,
            "med" : ErrorConfig.Metric.MED,
            "MED" : ErrorConfig.Metric.MED}
        if metric not in error_metrics.keys():
            raise ValueError(f"{metric}: error-metric not recognized")
        else:
            self.metric = error_metrics[metric]
        self.threshold = threshold
        self.n_vectors = vectors
        self.weights = weights

class HwConfig:
    class Metric(Enum):
        GATES = 1
        AREA = 2
        POWER = 3
        DEPTH = 5

    def __init__(self, metrics, liberty = None):
        hw_metrics = {
            "gates" : HwConfig.Metric.GATES,
            "area"  : HwConfig.Metric.AREA,
            "power" : HwConfig.Metric.POWER,
            "depth": HwConfig.Metric.DEPTH,
        }
        self.metrics = []
        for metric in metrics:
            if metric not in hw_metrics.keys():
                raise ValueError(f"{metric}: hw-metric not recognized")
            else:
                self.metrics.append(hw_metrics[metric])
        self.liberty = liberty
        if HwConfig.Metric.AREA in self.metrics or HwConfig.Metric.POWER in self.metrics:
            if self.liberty == None:
                raise ValueError(f"you need to specify a technology library for area or power optimization")
            else:
                library = parse_liberty(open(self.liberty).read())
                self.cell_area = {cell_group.args[0]: float(cell_group['area']) for cell_group in library.get_groups('cell')}
                self.cell_power = { cell_group.args[0] : float(cell_group['cell_leakage_power'] if cell_group['cell_leakage_power'] is not None else cell_group['drive_strength'] ) for cell_group in library.get_groups('cell') }
        else:
            self.cell_area = None
            self.cell_power = None

class MOP(AMOSA.Problem):
    def __init__(self, top_module, graph, catalog, error_config, hw_config):
        self.top_module = top_module
        self.graph = graph
        self.graphs = [copy.deepcopy(graph)] * cpu_count()
        self.rewriter = ALSRewriter(graph, catalog)
        self.n_vars = graph.get_num_cells()
        self.catalog = catalog
        self.error_config = error_config
        self.hw_config = hw_config
        self.samples = []
        self._generate_samples()
        if self.error_config.metric == ErrorConfig.Metric.EPROB:
            self.__args = [[g, s, [0] * self.n_vars] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))]
        else:
            self.__args = [[g, s, [0] * self.n_vars, self.error_config.weights] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))]
        self.upper_bound = self._get_upper_bound()
        self.baseline_and_gates = self._get_baseline_gates()
        print(f"# vars: {self.n_vars}, ub:{self.upper_bound}")
        print(f"Baseline requirements: {self.baseline_and_gates} AIG-nodes")
        AMOSA.Problem.__init__(self, self.n_vars, [AMOSA.Type.INTEGER] * self.n_vars, [0] * self.n_vars, self.upper_bound, len(self.hw_config.metrics) + 1, 1)

    def evaluate(self, x, out):
        configuration = self._matter_configuration(x)
        out["f"] = []
        out["g"] = []
        if self.error_config.metric == ErrorConfig.Metric.EPROB:
            out["f"].append(self._get_eprob(configuration))
        elif self.error_config.metric == ErrorConfig.Metric.AWCE:
            out["f"].append(self._get_awce(configuration))
        elif self.error_config.metric == ErrorConfig.Metric.MED:
            out["f"].append(self._get_med(configuration))
        out["g"].append(out["f"][-1] - self.error_config.threshold)

        area, power = 0, 0
        if HwConfig.Metric.AREA in self.hw_config.metrics or HwConfig.Metric.POWER in self.hw_config.metrics:
            area, power = self._get_hw(x)
        for metric in self.hw_config.metrics:
            if metric == HwConfig.Metric.GATES:
                out["f"].append(get_gates(configuration))
            elif metric == HwConfig.Metric.DEPTH:
                out["f"].append(get_depth(configuration, self.graph))
            elif metric == HwConfig.Metric.AREA:
                out["f"].append(area)
            elif metric == HwConfig.Metric.POWER:
                out["f"].append(power)

    def _generate_samples(self):
        PI = self.graph.get_pi()
        if self.error_config.n_vectors != 0:
            for _ in range(self.error_config.n_vectors):
                inputs = {i["name"]: bool(random.getrandbits(1)) for i in PI}
                self.samples.append({"input": inputs, "output": self.graph.evaluate(inputs)})
        else:
            self.error_config.n_vectors = 2 ** len(PI)
            permutations = [list(i) for i in itertools.product([False, True], repeat = len(PI))]
            for perm in permutations:
                inputs = {i["name"]: p for i, p in zip(PI, perm)}
                self.samples.append({"input": inputs, "output": self.graph.evaluate(inputs)})

    def _matter_configuration(self, x):
        return {l["name"]: {"dist": c, "spec": e[0]["spec"], "axspec": e[c]["spec"], "gates": e[c]["gates"], "S": e[c]["S"], "P": e[c]["P"], "out_p": e[c]["out_p"], "out": e[c]["out"], "depth": e[c]["depth"]} for c, l in zip(x, self.graph.get_cells()) for e in self.catalog if e[0]["spec"] == l["spec"]}

    def _get_upper_bound(self):
        cells = [{"name": c["name"], "spec": c["spec"]} for c in self.graph.get_cells()]
        return [len(e) - 1 for c in cells for e in self.catalog if e[0]["spec"] == c["spec"]]

    def _get_outputs(self, configuration):
        for a in self.__args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            outputs = pool.starmap(evaluate_output, self.__args)
        return [ o for output in outputs for o in output ]

    def _get_eprob(self, configuration):
        for a in self.__args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_eprob, self.__args)
        rs = sum(error) / self.error_config.n_vectors
        return rs + 4.5 / self.error_config.n_vectors * (1 + np.sqrt(1 + 4 / 9 * self.error_config.n_vectors * rs * (1 - rs)))

    def _get_awce(self, configuration):
        for a in self.__args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_awce, self.__args)
        return np.max(error)

    def _get_med(self, configuration):
        for a in self.__args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            hystogram = pool.starmap(evaluate_med, self.__args)
        return sum([i[0] * i[1] / (2 ** len(self.error_config.weights)) for i in dict(functools.reduce(operator.add, map(collections.Counter, hystogram))).items()])

    def _get_baseline_gates(self):
        return get_gates(self._matter_configuration([0] * self.n_vars))

    def _get_baseline_depth(self):
        return get_depth(self._matter_configuration([0] * self.n_vars))

    def _get_hw(self, x):
        design = self.rewriter.rewrite("original", x)
        ys.run_pass(f"tee -q synth -flatten -top {self.top_module}; tee -q clean -purge; tee -q read_liberty -lib {self.hw_config.liberty}; tee -q abc -liberty {self.hw_config.liberty};", design)
        f2 = get_area(design, self.hw_config.cell_area)
        f3 = get_power(design, self.hw_config.cell_power)
        ys.run_pass("tee -q clean", design)
        ys.run_pass("tee -q design -reset", design)
        ys.run_pass("tee -q delete", design)
        del design
        gc.collect()
        return f2, f3

def evaluate_output(graph, samples, configuration):
    return [{"e" : s["output"], "a" : graph.evaluate(s["input"], configuration)} for s in samples]

def evaluate_eprob(graph, samples, configuration):
    return sum([0 if sample["output"] == graph.evaluate(sample["input"], configuration) else 1 for sample in samples])

def evaluate_awce(graph, samples, configuration, weights):
    current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]
    return np.max([ sum([weights[o] if sample["output"][o] != current[o] else 0 for o in weights.keys() ]) for sample, current in zip(samples, current_outputs) ])

def evaluate_med(graph, samples, configuration, weights):
    error_hystogram = { i: 0 for i in range(2**len(weights)) }
    for sample in samples:
        current_output = graph.evaluate(sample["input"], configuration)
        error = sum([weights[o] if sample["output"][o] != current_output[o] else 0 for o in weights.keys()])
        error_hystogram[error] += 1
    return error_hystogram

def get_gates(configuration):
    return sum([c["gates"] for c in configuration.values()])

def get_depth(configuration, graph):
    return graph.get_depth(configuration)

def get_area(design, cell_area):
    return sum([cell_area[cell.type.str()[1:]] for module in design.selected_whole_modules_warn() for cell in module.selected_cells()])

def get_power(design, cell_power):
    return sum([cell_power[cell.type.str()[1:]] for module in design.selected_whole_modules_warn() for cell in module.selected_cells()])
