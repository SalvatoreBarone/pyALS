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
from .HwMetrics import *
from .ErrorMetrics import *
from .ALSRewriter import *
from .AMOSA import *

class ExhaustiveExploration:
    def __init__(self, top_module, graph, catalog, error_config, hw_config):
        self.top_module = top_module
        self.graph = graph
        self.graphs = [copy.deepcopy(graph)] * cpu_count()
        self.rewriter = ALSRewriter(graph, catalog)
        self.n_objs = len(hw_config.metrics) + 1
        self.n_vars = graph.get_num_cells()
        self.catalog = catalog
        self.error_config = error_config
        self.hw_config = hw_config
        self.samples = []
        self.duration = time.time()
        self._generate_samples()
        if self.error_config.metric == ErrorConfig.Metric.EPROB:
            self.__args = [[g, s, [0] * self.n_vars] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))]
        else:
            self.__args = [[g, s, [0] * self.n_vars, self.error_config.weights] for g, s in zip(self.graphs, list_partitioning(self.samples, cpu_count()))]
        self.upper_bound = self._get_upper_bound()
        self.baseline_and_gates = self._get_baseline_gates()
        print(f"#vars: {self.n_vars}, ub:{self.upper_bound}, #conf.s {np.prod([ x + 1 for x in self.upper_bound ])}.")
        print(f"Baseline requirements: {self.baseline_and_gates} AIG-nodes")
        print(f"Computing configurations. This may take quite a long time...")
        cartesian_space = [ range(i + 1) for i in self.upper_bound ]
        self.combinations = [ list(c) for c in itertools.product(*cartesian_space) ]
        self.comb_generation_time = time.time() - self.duration
        self.points = []

    def explore(self):
        self.points = []
        n_comb = len(self.combinations)
        single_evaluation = 0
        total = 0
        hours = 0
        minutes = 0
        for c, i in zip(self.combinations, range(n_comb)):
            print(f"  {i + 1}/{n_comb}. ETA: {hours}h {minutes}m                                                          ", end="\r", flush=True)
            point = { "x": c, "f": [], "g": []}
            single_evaluation = time.time()
            out = self.__evaluate(point["x"])
            single_evaluation = time.time() - single_evaluation
            total = single_evaluation * (n_comb - i)
            hours = int(total / 3600)
            minutes = int((total - hours * 3600) / 60)
            point["f"] = out["f"]
            point["g"] = out["g"]
            self.__add_to_archive(point)
        self.duration = time.time() - self.duration

    def pareto_front(self):
        return np.array([s["f"] for s in self.points])

    def pareto_set(self):
        return np.array([s["x"] for s in self.points])

    def plot_pareto(self, pdf_file, fig_title = "Pareto front", axis_labels = ["f0", "f1", "f2"]):
        F = self.pareto_front()
        if self.n_objs == 2:
            plt.figure(figsize=(10, 10), dpi=300)
            plt.plot(F[:, 0], F[:, 1], 'k.')
            plt.xlabel(axis_labels[0])
            plt.ylabel(axis_labels[1])
            plt.title(fig_title)
            plt.savefig(pdf_file, bbox_inches='tight', pad_inches=0)
        elif self.n_objs == 3:
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            ax.set_xlabel(axis_labels[0])
            ax.set_ylabel(axis_labels[1])
            ax.set_zlabel(axis_labels[2])
            plt.title(fig_title)
            ax.scatter(F[:, 0], F[:, 1], F[:, 2], marker='.', color='k')
            plt.tight_layout()
            plt.savefig(pdf_file, bbox_inches='tight', pad_inches=0)

    def save_results(self, csv_file):
        original_stdout = sys.stdout
        row_format = "{:};" * self.n_objs + "{:};" * self.n_vars
        with open(csv_file, "w") as file:
            sys.stdout = file
            print(row_format.format(*[f"f{i}" for i in range(self.n_objs)], *[f"x{i}" for i in range(self.n_vars)]))
            for f, x in zip(self.pareto_front(), self.pareto_set()):
                print(row_format.format(*f, *x))
        sys.stdout = original_stdout

    def __evaluate(self, x):
        configuration = self._matter_configuration(x)
        out = {"f": [], "g" :[]}
        area, power = 0, 0
        if HwConfig.Metric.AREA in self.hw_config.metrics or HwConfig.Metric.POWER in self.hw_config.metrics:
            # this should be performed by a different process, in order to prevent memory leaks
            area, power = self._get_hw(x)
        if self.error_config.metric == ErrorConfig.Metric.EPROB:
            out["f"].append(self._get_eprob(configuration))
        elif self.error_config.metric == ErrorConfig.Metric.AWCE:
            out["f"].append(self._get_awce(configuration))
        elif self.error_config.metric == ErrorConfig.Metric.MED:
            out["f"].append(self._get_med(configuration))
        out["g"].append(out["f"][-1] - self.error_config.threshold)

        if HwConfig.Metric.AREA in self.hw_config.metrics or HwConfig.Metric.POWER in self.hw_config.metrics:
            # join
            pass

        for metric in self.hw_config.metrics:
            if metric == HwConfig.Metric.GATES:
                out["f"].append(get_gates(configuration))
            elif metric == HwConfig.Metric.DEPTH:
                out["f"].append(get_depth(configuration, self.graph))
            elif metric == HwConfig.Metric.AREA:
                out["f"].append(area)
            elif metric == HwConfig.Metric.POWER:
                out["f"].append(power)
        return out

    def __add_to_archive(self, x):
        if len(self.points) == 0:
            self.points.append(x)
        else:
            self.points = [y for y in self.points if not dominates(x, y)]
            if not any([dominates(y, x) or is_the_same(x, y) for y in self.points]):
                self.points.append(x)

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