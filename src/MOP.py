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
import sys, os, itertools, collections, functools, operator
from multiprocessing import cpu_count, Pool
from .HwMetrics import *
from .ErrorMetrics import *
from .ALSGraph import *
from .Utility import *
from .ALSRewriter import *

from pyAMOSA.AMOSA import *


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
        self.baseline_depth = self._get_baseline_depth()
        self.baseline_switching = self._get_baseline_switching()
        print(f"#vars: {self.n_vars}, ub:{self.upper_bound}, #conf.s {np.prod([ x + 1 for x in self.upper_bound ])}.")
        print(f"Baseline requirements. Nodes: {self.baseline_and_gates}. Depth: {self.baseline_depth}. Switching: {self.baseline_switching}")
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
        for metric in self.hw_config.metrics:
            if metric == HwConfig.Metric.GATES:
                out["f"].append(get_gates(configuration))
            elif metric == HwConfig.Metric.DEPTH:
                out["f"].append(get_depth(configuration, self.graph))
            elif metric == HwConfig.Metric.SWITCHING:
                out["f"].append(get_switching(configuration))

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
        if self.error_config.n_vectors != 0:
            return rs + 4.5 / self.error_config.n_vectors * (1 + np.sqrt(1 + 4 / 9 * self.error_config.n_vectors * rs * (1 - rs)))
        else:
            return rs

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
        den = 2 ** len(self.error_config.weights)
        return sum([ i[0] * i[1] / den for i in dict(functools.reduce(operator.add, map(collections.Counter, hystogram))).items() ])

    def _get_baseline_gates(self):
        return get_gates(self._matter_configuration([0] * self.n_vars))

    def _get_baseline_depth(self):
        return get_depth(self._matter_configuration([0] * self.n_vars,), self.graph)

    def _get_baseline_switching(self):
        return get_switching(self._matter_configuration([0] * self.n_vars))

