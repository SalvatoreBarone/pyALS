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
import random
from multiprocessing import cpu_count, Pool
from enum import Enum
from .AMOSA import *
from .ALSGraph import *
from .Utility import *

class ErrorConfig:
    class Metric(Enum):
        ERS = 1
        AWCE = 2

    def __init__(self, metric, threshold, vectors):
        error_metrics = {"ers": ErrorConfig.Metric.ERS, "awce": ErrorConfig.Metric.AWCE}
        if metric not in ["ers", "awce"]:
            raise ValueError(f"{metric}: error-metric not recognized")
        else:
            self.technique = error_metrics[metric]
        self.threshold = threshold
        self.n_vectors = vectors


class ERS(AMOSA.Problem):
    def __init__(self, graph, catalog, n_vectors, threshold):
        self.graph = graph
        graphs = [copy.deepcopy(graph)] * cpu_count()
        n_vars = graph.get_num_cells()
        self.catalog = catalog
        self.n_vectors = n_vectors
        self.threshold = threshold
        samples = []
        PI = graph.get_pi()
        for _ in range(self.n_vectors):
            input = [{"name": i["name"], "value": bool(random.getrandbits(1))} for i in PI]
            samples.append({"input": input, "output": graph.evaluate(input)})
        self.__args = [[g, s, [0] * n_vars] for g, s in zip(graphs, list_partitioning(samples, cpu_count()))]
        cells = [{"name": c["name"], "spec": c["spec"]} for c in graph.get_cells()]
        upper_bound = [len(e) - 1 for c in cells for e in catalog if e[0]["spec"] == c["spec"]]
        AMOSA.Problem.__init__(self, n_vars, [AMOSA.Type.INTEGER] * n_vars, [0] * n_vars, upper_bound, 2, 1)
        configuration = self._matter_configuration([0] * n_vars)
        and_gates = sum([c["gates"] for c in configuration])
        print(f"# vars: {n_vars}, ub:{upper_bound}")
        print(f"Baseline requirements: {and_gates} AIG-nodes")

    def _matter_configuration(self, x):
        return [{"name": l["name"], "dist": c, "spec": e[0]["spec"], "axspec": e[c]["spec"], "gates": e[c]["gates"],
                 "S": e[c]["S"], "P": e[c]["P"], "out_p": e[c]["out_p"], "out": e[c]["out"]} for c, l in
                zip(x, self.graph.get_cells()) for e in self.catalog if e[0]["spec"] == l["spec"]]

    def evaluate(self, x, out):
        configuration = self._matter_configuration(x)
        for a in self.__args:
            a[2] = configuration
        with Pool(cpu_count()) as pool:
            error = pool.starmap(evaluate_vectors, self.__args)
        rs = sum(error) / self.n_vectors
        f1 = rs + 4.5 / self.n_vectors * (1 + np.sqrt(1 + 4 / 9 * self.n_vectors * rs * (1-rs)))
        f2 = sum([c["gates"] for c in configuration])
        g1 = f1 - self.threshold
        out["f"] = [f1, f2]
        out["g"] = [g1]

def evaluate_vectors(graph, samples, configuration):
    return sum([0 if sample["output"] == graph.evaluate(sample["input"], configuration) else 1 for sample in samples])
