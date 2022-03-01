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
import sys, copy, random, time
import numpy as np
import matplotlib.pyplot as plt
from enum import Enum

class AMOSAConfig:
    def __init__(
            self,
            archive_hard_limit = 20,
            archive_soft_limit = 50,
            archive_gamma = 2,
            hill_climbing_iterations = 500,
            initial_temperature = 500,
            final_temperature = 0.000001,
            cooling_factor = 0.9,
            annealing_iterations = 500,
            early_termination_window = 10
            ):
        self.archive_hard_limit = archive_hard_limit
        self.archive_soft_limit = archive_soft_limit
        self.archive_gamma = archive_gamma
        self.hill_climbing_iterations = hill_climbing_iterations
        self.initial_temperature = initial_temperature
        self.final_temperature = final_temperature
        self.cooling_factor = cooling_factor
        self.annealing_iterations = annealing_iterations
        self.early_terminator_window = early_termination_window

class AMOSA:
    class Type(Enum):
        INTEGER = 0
        REAL = 1

    class Problem:
        def __init__(self, num_of_variables, types, lower_bounds, upper_bounds, num_of_objectives, num_of_constraints):
            self.num_of_variables = num_of_variables
            self.types = types
            self.lower_bound = lower_bounds
            self.upper_bound = upper_bounds
            self.num_of_objectives = num_of_objectives
            self.num_of_constraints = num_of_constraints

        def evaluate(self, x, out):
            pass

    def __init__(self,
            archive_hard_limit,
            archive_soft_limit,
            archive_gamma,
            hill_climbing_iterations,
            initial_temperature,
            final_temperature,
            cooling_factor,
            annealing_iterations,
            early_termination_window):
        self.__archive_hard_limit = archive_hard_limit
        self.__archive_soft_limit = archive_soft_limit
        self.__archive_gamma = archive_gamma
        self.__hill_climbing_iterations = hill_climbing_iterations
        self.__initial_temperature = initial_temperature
        self.__final_temperature = final_temperature
        self.__cooling_factor = cooling_factor
        self.__annealing_iterations = annealing_iterations
        self.__early_termination_window = early_termination_window
        self.__current_temperature = 0
        self.__archive = []
        self.duration = 0
        self.__n_eval = 0
        self.__ideal = None
        self.__nadir = None
        self.__old_f = []
        self.__phy = []

    def __init__(self, config):
        self.__archive_hard_limit = config.archive_hard_limit
        self.__archive_soft_limit = config.archive_soft_limit
        self.__archive_gamma = config.archive_gamma
        self.__hill_climbing_iterations = config.hill_climbing_iterations
        self.__initial_temperature = config.initial_temperature
        self.__final_temperature = config.final_temperature
        self.__cooling_factor = config.cooling_factor
        self.__annealing_iterations = config.annealing_iterations
        self.__early_termination_window = config.annealing_iterations
        self.__current_temperature = 0
        self.__archive = []
        self.duration = 0
        self.__n_eval = 0
        self.__ideal = None
        self.__nadir = None
        self.__old_f = []
        self.__phy = []

    def minimize(self, problem):
        self.__parameters_check()
        self.__archive = []
        self.__old_f = None
        self.__phy = []
        self.__ideal = None
        self.__nadir = None
        self.duration = time.time()
        self.__initialize_archive(problem)
        if len(self.__archive) > self.__archive_hard_limit:
            self.__archive_clustering(problem)
        self.__print_header(problem)
        self.__current_temperature = self.__initial_temperature
        x = random.choice(self.__archive)
        self.__print_statistics(problem)
        while self.__current_temperature > self.__final_temperature:
            for i in range(self.__annealing_iterations):
                y = random_perturbation(problem, x)
                fitness_range = self.__compute_fitness_range(x, y)
                s_dominating_y = [s for s in self.__archive if dominates(s, y)]
                k_s_dominating_y = len(s_dominating_y)
                s_dominated_by_y = [s for s in self.__archive if dominates(y, s)]
                k_s_dominated_by_y = len(s_dominated_by_y)
                if dominates(x, y) and k_s_dominating_y >= 0:
                    delta_avg = (sum([domination_amount(s, y, fitness_range) for s in s_dominating_y]) + domination_amount(x, y, fitness_range)) / (k_s_dominating_y + 1)
                    if accept(sigmoid(-delta_avg * self.__current_temperature)):
                        x = y
                elif not dominates(x, y) and not dominates(y, x):
                    if k_s_dominating_y >= 1:
                        delta_avg = sum([domination_amount(s, y, fitness_range) for s in s_dominating_y])  / k_s_dominating_y
                        if accept(sigmoid(-delta_avg * self.__current_temperature)):
                            x = y
                    elif (k_s_dominating_y == 0 and k_s_dominated_by_y == 0) or k_s_dominated_by_y >= 1:
                        self.__add_to_archive(y)
                        if len(self.__archive) > self.__archive_soft_limit:
                            self.__archive_clustering(problem)
                        x = y
                elif dominates(y, x):
                    if k_s_dominating_y >= 1:
                        delta_dom = [domination_amount(s, y, fitness_range) for s in s_dominating_y]
                        if accept(sigmoid(min(delta_dom))):
                            x = self.__archive[np.argmin(delta_dom)]
                    elif (k_s_dominating_y == 0 and k_s_dominated_by_y == 0) or k_s_dominated_by_y >= 1:
                        self.__add_to_archive(y)
                        if len(self.__archive) > self.__archive_soft_limit:
                            self.__archive_clustering(problem)
                        x = y
                else:
                    raise RuntimeError(f"Something went wrong\narchive: {self.__archive}\nx:{x}\ny: {y}\n x < y: {dominates(x, y)}\n y < x: {dominates(y, x)}\ny domination rank: {k_s_dominated_by_y}\narchive domination rank: {k_s_dominating_y}")
            self.__print_statistics(problem)
            if self.__early_termination_window == 0:
                self.__current_temperature *= self.__cooling_factor
            else:
                if self.__phy[-self.__early_termination_window:] == 0:
                    print("The early-termination criterion has been met!")
                    self.__current_temperature = self.__final_temperature
                else:
                    self.__current_temperature *= self.__cooling_factor
        if len(self.__archive) > self.__archive_hard_limit:
            self.__archive_clustering(problem)
        self.__remove_infeasible(problem)
        self.__print_statistics(problem)
        self.duration = time.time() - self.duration

    def pareto_front(self):
        return np.array([s["f"] for s in self.__archive])

    def pareto_set(self):
        return np.array([s["x"] for s in self.__archive])

    def constraint_violation(self):
        return np.array([s["g"] for s in self.__archive])

    def plot_pareto(self, problem, pdf_file, fig_title = "Pareto front", axis_labels = ["f0", "f1", "f2"]):
        F = self.pareto_front()
        if problem.num_of_objectives == 2:
            plt.figure(figsize=(10, 10), dpi=300)
            plt.plot(F[:, 0], F[:, 1], 'k.')
            plt.xlabel(axis_labels[0])
            plt.ylabel(axis_labels[1])
            plt.title(fig_title)
            plt.savefig(pdf_file, bbox_inches='tight', pad_inches=0)
        elif problem.num_of_objectives == 3:
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            ax.set_xlabel(axis_labels[0])
            ax.set_ylabel(axis_labels[1])
            ax.set_zlabel(axis_labels[2])
            plt.title(fig_title)
            ax.scatter(F[:, 0], F[:, 1], F[:, 2], marker='.', color='k')
            plt.tight_layout()
            plt.savefig(pdf_file, bbox_inches='tight', pad_inches=0)

    def save_results(self, problem, csv_file):
        original_stdout = sys.stdout
        row_format = "{:};" * problem.num_of_objectives + "{:};" * problem.num_of_variables
        with open(csv_file, "w") as file:
            sys.stdout = file
            print(row_format.format(*[f"f{i}" for i in range(problem.num_of_objectives)], *[f"x{i}" for i in range(problem.num_of_variables)]))
            for f, x in zip(self.pareto_front(), self.pareto_set()):
                print(row_format.format(*f, *x))
        sys.stdout = original_stdout

    def __parameters_check(self):
        if self.__archive_hard_limit > self.__archive_soft_limit:
            raise RuntimeError("Hard limit must be greater than the soft one")
        if self.__hill_climbing_iterations < 0:
            raise RuntimeError("Initial hill-climbing refinement iterations must be greater or equal than 0")
        if self.__archive_gamma < 1:
            raise RuntimeError("Gamma for initial hill-climbing refinement must be greater than 1")
        if self.__annealing_iterations < 1:
            raise RuntimeError("Refinement iterations must be greater than 1")
        if self.__final_temperature <= 0:
            raise RuntimeError("Final temperature of the matter must be greater or equal to 0")
        if self.__initial_temperature <= self.__final_temperature:
            raise RuntimeError("Initial temperature of the matter must be greater than the final one")
        if self.__cooling_factor <= 0 or self.__cooling_factor >= 1:
            raise RuntimeError("The cooling factor for the temperature of the matter must be in the (0, 1) range")

    def __initialize_archive(self, problem):
        print("Initializing archive...")
        self.__n_eval = self.__archive_gamma * self.__archive_soft_limit * self.__hill_climbing_iterations
        num_of_initial_candidate_solutions = self.__archive_gamma * self.__archive_soft_limit
        initial_candidate_solutions = [lower_point(problem), upper_point(problem)]
        if self.__hill_climbing_iterations > 0:
            for i in range(num_of_initial_candidate_solutions):
                print(f"  {i + 1}/{num_of_initial_candidate_solutions}                                                  ", end = "\r", flush = True)
                initial_candidate_solutions.append(hill_climbing(problem, random_point(problem), self.__hill_climbing_iterations))
        for x in initial_candidate_solutions:
            self.__add_to_archive(x)

    def __add_to_archive(self, x):
        if len(self.__archive) == 0:
            self.__archive.append(x)
        else:
            self.__archive = [y for y in self.__archive if not dominates(x, y)]
            if not any([dominates(y, x) or is_the_same(x, y) for y in self.__archive]):
                self.__archive.append(x)

    def __archive_clustering(self, problem):
        if problem.num_of_constraints > 0:
            feasible = [s for s in self.__archive if all([g <= 0 for g in s["g"]])]
            non_feasible = [s for s in self.__archive if all([g > 0 for g in s["g"]])]
            if len(feasible) > self.__archive_hard_limit:
                do_clustering(feasible, self.__archive_hard_limit)
                self.__archive = feasible
            else:
                do_clustering(non_feasible, self.__archive_hard_limit - len(feasible))
                self.__archive = non_feasible + feasible
        else:
            do_clustering(self.__archive, self.__archive_hard_limit)

    def __remove_infeasible(self, problem):
        if problem.num_of_constraints > 0:
            self.__archive = [s for s in self.__archive if all([g <= 0 for g in s["g"]])]

    def __print_header(self, problem):
        if problem.num_of_constraints == 0:
            print("\n  +-{:>12}-+-{:>10}-+-{:>6}-+-{:>10}-+-{:>10}-+-{:>10}-+".format("-" * 12, "-" * 10, "-" * 6, "-" * 10, "-" * 10, "-" * 10))
            print("  | {:>12} | {:>10} | {:>6} | {:>10} | {:>10} | {:>10} |".format("temp.", "# eval", " # nds", "D*", "Dnad", "phi"))
            print("  +-{:>12}-+-{:>10}-+-{:>6}-+-{:>10}-+-{:>10}-+-{:>10}-+".format("-" * 12, "-" * 10, "-" * 6, "-" * 10, "-" * 10, "-" * 10))
        else:
            print("\n  +-{:>12}-+-{:>10}-+-{:>6}-+-{:>6}-+-{:>10}-+-{:>10}-+-{:>10}-+-{:>10}-+-{:>10}-+".format("-" * 12, "-" * 10, "-" * 6, "-" * 6, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10))
            print("  | {:>12} | {:>10} | {:>6} | {:>6} | {:>10} | {:>10} | {:>10} | {:>10} | {:>10} |".format("temp.", "# eval", "# nds", "# feas", "cv min", "cv avg", "D*", "Dnad", "phi"))
            print("  +-{:>12}-+-{:>10}-+-{:>6}-+-{:>6}-+-{:>10}-+-{:>10}-+-{:>10}-+-{:>10}-+-{:>10}-+".format("-" * 12, "-" * 10, "-" * 6, "-" * 6, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10))

    def __print_statistics(self, problem):
        self.__n_eval += self.__annealing_iterations
        delta_nad, delta_ideal, phy = self.__compute_deltas()
        self.__phy.append(phy)
        if problem.num_of_constraints == 0:
            print("  | {:>12.2e} | {:>10.2e} | {:>6} | {:>10.3e} | {:>10.3e} | {:>10.3e} |".format(self.__current_temperature, self.__n_eval, len(self.__archive), delta_ideal, delta_nad, phy))
        else:
            feasible, cv_min, cv_avg = self.__compute_cv()
            print("  | {:>12.2e} | {:>10.2e} | {:>6} | {:>6} | {:>10.2e} | {:>10.2e} | {:>10.3e} | {:>10.3e} | {:>10.3e} |".format(self.__current_temperature, self.__n_eval, len(self.__archive), feasible, cv_min, cv_avg, delta_ideal, delta_nad, phy))

    def __compute_cv(self):
        g = np.array([s["g"] for s in self.__archive ])
        feasible = np.all(np.less(g, 0), axis=1).sum()
        g = g[np.where(g > 0)]
        return feasible, 0 if len(g) == 0 else np.min(g), 0 if len(g) == 0 else np.average(g)

    def __compute_deltas(self):
        f = np.array([s["f"] for s in self.__archive])
        if self.__nadir is None and self.__ideal is None and self.__old_f is None:
            self.__nadir = np.max(f, axis=0)
            self.__ideal = np.min(f, axis=0)
            self.__old_f = np.array([[(p - i) / (n - i) for p, i, n in zip(x, self.__ideal, self.__nadir) ] for x in f[:] ])
            return np.inf, np.inf, 0
        else:
            nadir = np.max(f, axis=0)
            ideal = np.min(f, axis=0)
            delta_nad = np.max([(nad_t_1 - nad_t) / (nad_t_1 - id_t) for nad_t_1, nad_t, id_t in zip(self.__nadir, nadir, ideal)])
            delta_ideal = np.max([(id_t_1 - id_t) / (nad_t_1 - id_t) for id_t_1, id_t, nad_t_1 in zip(self.__ideal, ideal, self.__nadir)])
            f = np.array([[(p - i) / (n - i) for p, i, n in zip(x, self.__ideal, self.__nadir) ] for x in f[:] ])
            phy = sum([np.min([np.linalg.norm(p - q) for q in f[:]]) for p in self.__old_f[:]]) / len(self.__old_f)
            self.__nadir = nadir
            self.__ideal = ideal
            self.__old_f = f
            return delta_nad, delta_ideal, phy

    def __compute_fitness_range(self, x, y):
        f = [s["f"] for s in self.__archive] + [x["f"], y["f"]]
        return np.max(f, axis = 0) - np.min(f, axis=0)

def hill_climbing(problem, x, max_iterations):
    d, up = hill_climbing_direction(problem)
    for _ in range(max_iterations):
        y = copy.deepcopy(x)
        hill_climbing_adaptive_step(problem, y, d, up)
        if dominates(y, x) and not_the_same(y, x):
            x = y
        else:
            d, up = hill_climbing_direction(problem, d)
    return x

def random_point(problem):
    x = {
        "x": [ l if l == u else random.randrange(l, u) if t == AMOSA.Type.INTEGER else random.uniform(l, u) for l, u, t in zip(problem.lower_bound, problem.upper_bound, problem.types)],
        "f": [0] * problem.num_of_objectives,
        "g": [0] * problem.num_of_constraints if problem.num_of_constraints > 0 else None}
    get_objectives(problem, x)
    return x

def lower_point(problem):
    x = {
        "x": problem.lower_bound,
        "f": [0] * problem.num_of_objectives,
        "g": [0] * problem.num_of_constraints if problem.num_of_constraints > 0 else None}
    get_objectives(problem, x)
    return x

def upper_point(problem):
    x = {
        "x": problem.upper_bound,
        "f": [0] * problem.num_of_objectives,
        "g": [0] * problem.num_of_constraints if problem.num_of_constraints > 0 else None}
    get_objectives(problem, x)
    return x

def random_perturbation(problem, s):
    z = copy.deepcopy(s)
    step = 0
    d, up = hill_climbing_direction(problem)
    while step == 0:
        d, up = hill_climbing_direction(problem)
        lower_bound = problem.lower_bound[d] - z["x"][d]
        upper_bound = problem.upper_bound[d] - z["x"][d]
        if (up == -1 and lower_bound == 0) or (up == 1 and upper_bound == 0):
            continue
        if problem.types[d] == AMOSA.Type.INTEGER:
            step = random.randrange(lower_bound, 0) if up == -1 else random.randrange(0, upper_bound + 1)
        else:
            step = random.uniform(lower_bound, 0) if up == -1 else random.uniform(0, upper_bound)
    z["x"][d] += step
    get_objectives(problem, z)
    return z

def hill_climbing_direction(problem, c_d = None):
    if c_d is None:
        return random.randrange(0, problem.num_of_variables), 1 if random.random() > 0.5 else -1
    else:
        up = 1 if random.random() > 0.5 else -1
        d = random.randrange(0, problem.num_of_variables)
        while c_d == d:
            d = random.randrange(0, problem.num_of_variables)
        return d, up

def hill_climbing_adaptive_step(problem, s, d, up):
    lower_bound = problem.lower_bound[d] - s["x"][d]
    upper_bound = problem.upper_bound[d] - s["x"][d]
    if (up == -1 and lower_bound == 0) or (up == 1 and upper_bound == 0):
        return 0
    if problem.types[d] == AMOSA.Type.INTEGER:
        step = random.randrange(lower_bound, 0) if up == -1 else random.randrange(0, upper_bound + 1)
        while step == 0:
            step = random.randrange(lower_bound, 0) if up == -1 else random.randrange(0, upper_bound + 1)
    else:
        step = random.uniform(lower_bound, 0) if up == -1 else random.uniform(0, upper_bound)
        while step == 0:
            step = random.uniform(lower_bound, 0) if up == -1 else random.uniform(0, upper_bound)
    s["x"][d] += step
    get_objectives(problem, s)

def do_clustering(archive, hard_limit):
    while len(archive) > hard_limit:
        d = np.array([[np.linalg.norm(np.array(i["f"]) - np.array(j["f"])) if not np.array_equal(np.array(i["x"]), np.array(j["x"])) else np.nan for j in archive] for i in archive])
        try:
            i_min = np.nanargmin(d)
            r = int(i_min / len(archive))
            c = i_min % len(archive)
            del archive[r if np.where(d[r] == np.nanmin(d[r]))[0].size > np.where(d[c] == np.nanmin(d[c]))[0].size else c]
        except:
            # print("Clustering cannot be performed anymore")
            return

def get_objectives(problem, s):
    out = {"f": [0] * problem.num_of_objectives,
           "g": [0] * problem.num_of_constraints if problem.num_of_constraints > 0 else None}
    problem.evaluate(s["x"], out)
    s["f"] = out["f"]
    s["g"] = out["g"]

def is_the_same(x, y):
    return x["x"] == y["x"]

def not_the_same(x, y):
    return x["x"] != y["x"]

def dominates(x, y):
    if x["g"] is None:
        return all( i <= j for i, j in zip(x["f"], y["f"]) ) and any( i < j for i, j in zip(x["f"], y["f"]) )
    else:
        return  ((all(i <= 0 for i in x["f"]) and any(i > 0 for i in y["g"])) or # x is feasible while y is not
                 (any(i > 0 for i in x["g"]) and any(i > 0 for i in y["g"]) and all([ i <= j for i, j in zip(x["g"], y["g"]) ]) and any([ i < j for i, j in zip(x["g"], y["g"]) ])) or #x and y are both infeasible, but x has a lower constraint violation
                 (all(i <= 0 for i in x["g"]) and all(i <= 0 for i in y["g"]) and all([ i <= j for i, j in zip(x["f"], y["f"]) ]) and any([ i < j for i, j in zip(x["f"], y["f"]) ]))) # both are feasible, but x dominates y in the usual sense

def accept(probability):
    return random.random() < probability

def domination_amount(x, y, r):
    return np.prod([ abs(i - j) / k for i, j, k in zip (x["f"], y["f"], r) ])

def sigmoid(x):
    return 1 / (1 + np.exp(np.array(-x, dtype=np.float128)))
