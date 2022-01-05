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
import random, itertools, collections, functools, operator
from multiprocessing import cpu_count, Pool
from enum import Enum
from .AMOSA import *
from .ALSGraph import *
from .Utility import *

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

class ErrorEvaluator:
    def __init__(self, graph, catalog, n_vectors, threshold):
        self.graph = graph
        self.graphs = [copy.deepcopy(graph)] * cpu_count()
        self.n_vars = graph.get_num_cells()
        self.catalog = catalog
        self.n_vectors = n_vectors
        self.threshold = threshold
        self.samples = []
        PI = graph.get_pi()
        if self.n_vectors != 0:
            for _ in range(self.n_vectors):
                inputs = { i["name"]: bool(random.getrandbits(1)) for i in PI }
                self.samples.append({"input": inputs, "output": graph.evaluate(inputs)})
        else:
            # exhaustive simulations
            n_inputs = len(graph.get_pi())
            self.n_vectors = 2 ** n_inputs
            permutations = [list(i) for i in itertools.product([False, True], repeat = n_inputs)]
            for perm in permutations:
                inputs = { i["name"] : p for i, p in zip(PI, perm) }
                self.samples.append({"input": inputs, "output": graph.evaluate(inputs)})
        cells = [{"name": c["name"], "spec": c["spec"]} for c in graph.get_cells()]
        self.upper_bound = [len(e) - 1 for c in cells for e in catalog if e[0]["spec"] == c["spec"]]
        configuration = self._matter_configuration([0] * self.n_vars)
        self.baseline_and_gates = self._get_gates(configuration)
        print(f"# vars: {self.n_vars}, ub:{self.upper_bound}")
        print(f"Baseline requirements: {self.baseline_and_gates} AIG-nodes")

    def _matter_configuration(self, x):
        return [{"name": l["name"], "dist": c, "spec": e[0]["spec"], "axspec": e[c]["spec"], "gates": e[c]["gates"],
                 "S": e[c]["S"], "P": e[c]["P"], "out_p": e[c]["out_p"], "out": e[c]["out"]} for c, l in
                zip(x, self.graph.get_cells()) for e in self.catalog if e[0]["spec"] == l["spec"]]

    def _get_gates(self, configuration):
        return sum([c["gates"] for c in configuration])

class ErrorProbability(ErrorEvaluator, AMOSA.Problem):
    def __init__(self, graph, catalog, n_vectors, threshold):
        ErrorEvaluator.__init__(self, graph, catalog, n_vectors, threshold)
        self.__args = [[g, s, [0] * self.n_vars] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))]
        AMOSA.Problem.__init__(self, self.n_vars, [AMOSA.Type.INTEGER] * self.n_vars, [0] * self.n_vars, self.upper_bound, 2, 1)

    def evaluate(self, x, out):
        configuration = self._matter_configuration(x)
        for a in self.__args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_eprob, self.__args)
        rs = sum(error) / self.n_vectors
        f1 = rs + 4.5 / self.n_vectors * (1 + np.sqrt(1 + 4 / 9 * self.n_vectors * rs * (1-rs)))
        f2 = self._get_gates(configuration)
        g1 = f1 - self.threshold
        out["f"] = [f1, f2]
        out["g"] = [g1]


def evaluate_eprob(graph, samples, configuration):
    return sum([0 if sample["output"] == graph.evaluate(sample["input"], configuration) else 1 for sample in samples])

class AWCE(ErrorEvaluator, AMOSA.Problem):
    def __init__(self, graph, catalog, n_vectors, threshold, weights):
        self.weights = weights
        ErrorEvaluator.__init__(self, graph, catalog, n_vectors, threshold)
        self.__args = [[g, s, [0] * self.n_vars, self.weights] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))]
        AMOSA.Problem.__init__(self, self.n_vars, [AMOSA.Type.INTEGER] * self.n_vars, [0] * self.n_vars, self.upper_bound, 2, 1)

    def evaluate(self, x, out):
        configuration = self._matter_configuration(x)
        for a in self.__args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_awce, self.__args)
        f1 = np.max(error)
        f2 = self._get_gates(configuration)
        g1 = f1 - self.threshold
        out["f"] = [f1, f2]
        out["g"] = [g1]

def evaluate_awce(graph, samples, configuration, weights):
    current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]
    return np.max([ sum([weights[o] if sample["output"][o] != current[o] else 0 for o in weights.keys() ]) for sample, current in zip(samples, current_outputs) ])

class MED(ErrorEvaluator, AMOSA.Problem):
    def __init__(self, graph, catalog, n_vectors, threshold, weights):
        self.weights = weights
        ErrorEvaluator.__init__(self, graph, catalog, n_vectors, threshold)
        self.__args = [[g, s, [0] * self.n_vars, self.weights] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))]
        AMOSA.Problem.__init__(self, self.n_vars, [AMOSA.Type.INTEGER] * self.n_vars, [0] * self.n_vars, self.upper_bound, 2, 1)

    def evaluate(self, x, out):
        configuration = self._matter_configuration(x)
        for a in self.__args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            hystogram = pool.starmap(evaluate_med, self.__args)
        f1 = sum([i[0] * i[1] / (2**len(self.weights)) for i in dict(functools.reduce(operator.add, map(collections.Counter, hystogram))).items()])
        f2 = self._get_gates(configuration)
        g1 = f1 - self.threshold
        out["f"] = [f1, f2]
        out["g"] = [g1]

def evaluate_med(graph, samples, configuration, weights):
    error_hystogram = { i: 0 for i in range(2**len(weights)) }
    for sample in samples:
        current_output = graph.evaluate(sample["input"], configuration)
        error = sum([weights[o] if sample["output"][o] != current_output[o] else 0 for o in weights.keys()])
        error_hystogram[error] += 1
    return error_hystogram