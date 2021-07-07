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
import sys
import numpy as np
from pymoo.model.problem import Problem
from pymoo.algorithms.nsga2 import NSGA2
from pymoo.factory import get_sampling, get_crossover, get_mutation, get_termination
from pymoo.optimize import minimize
from pyosys import libyosys as ys
from .ALSEvaluator import *

"""
@brief Implements the multi-objective optimization problem through which the design-space exploration phase is driven.

@details
As stated in Kalyanmoy Deb "Multi-Objective Optimization Using Evolutionary Algorithms" John Wiley & Sons, Inc., New 
York, NY, USA, 2001. ISBN 047187339X, a multi-objective optimization problem (MOP) has several objective functions with
subject to inequality and equality constraints to optimize. The goal is to find a set of solutions that do not have any
constraint violation and are as good as possible regarding all its objectives values.
The problem definition in its general form is given by the following equations, which define MOP with N variables, M 
objectives, J inequality and K equality constraints. Moreover, for each variable, both the lower and upper variable 
boundaries are defined.

\f{eqnarray*}[ 
 min/max  f_m(x) \; m=1 \cdots M \\
 s.t.   g_j(x) \leq 0 \;j=1 \cdots J \\
        h_k(x) = 0 \; k = 1 \cdots K \\
        x_i^L \leq x_i \leq x_i^U \; i = 1 \cdots N
\f}

In order to perform multi-objective optimization, the Optimizer class exploits the NSGA-II implementation provided by
the pymoo module, which requires the following
  1. Implementation of a Problem (element-wise class, in our case)
  2. Initialization of an Algorithm (in our case, NSGA-II)
  3. Definition of a Termination Criterion (the number of NSGA-II generations)
  4. Optimize (minimize error and hardware requirements, in our case)
"""
class ALSOptimizer:
  """
  @brief Implementation fo a Problem
  """
  class MOP(Problem):
    """
    @brief Constructor. Instantiate a new optimization problem.

    @details
    Phenotype genotype encoding: 
    k-LUTs nodes of the considered circuit constitute the set of decision variables of the optimization problem, and
    their domain is given by catalog entries.

    Each chromosome consists of a number of genes that is equal to the LUT instances within the considered circuit. 
    The value assigned to a given gene governs the Hamming distance between the original (non-approximate) LUT 
    specification at the corresponding circuit node, and the one to be adopted, i.e. a value of 0 determines the 
    non-approximate LUT specification to be used while a value of 1 determines the LUT specification at Hamming distance
    1 to be used, and so forth.
    
    The gene-node correspondence is assigned according to the topological ordering defined by the underlying graph.

    @param [in] design      Yosys top-module instance

    @param [in] catalog     catalog of approximate LUTs.

    @param [in] nvectors    number of random test vectors for error evaluation

    @note
    pymoo provides three different ways of defining a problem, i.e. 
      - by class, which includes
        - vectorized evaluation: a set of solutions is evaluated directly.
        - elementwise evaluation: only one solution is evaluated at a time.
      - by Functions: functional interface as commonly defined in other optimization libraries.
    .
    Here, the element-wise class implementation is considered. Defining a problem through a class allows defining the
    problem very naturally, assuming the metadata, such as the number of variables and objectives, are known. The
    MOP class inherits from the Problem class. By calling the super() function in the constructor __init__ the problem
    properties such as the number of variables n_var, objectives n_obj and constraints n_constr are supposed to be
    initialized. Furthermore, lower xl and upper variables boundaries xu are supplied as a NumPy array.
    """
    def __init__(self, design, catalog, evaluator):
      self.__design = design
      self.__catalog = catalog
      self.__evaluator = evaluator

      # get the list of LUTs within the given circuit, in order to determine the number of needed genes
      self.__lut_list = [ cell.parameters[ys.IdString("\LUT")] for module in self.__design.selected_whole_modules_warn() for cell in module.selected_cells() if ys.IdString("\LUT") in cell.parameters ]
      ngenes = len (self.__lut_list)
      # the lower bound for genes is always 0 (no approximation)
      lower_bounds = np.zeros(ngenes, dtype = np.uint32)
      # the upper bound for genes is given by the amount of catalog entries for a certain function specification (minus one)
      # for each of the LUTs within the circuit, get the amount of catalog entries, i.e. the range [0, N) for each gene
      entries_available = [ len(entry) for lut in self.__lut_list for entry in self.__catalog if entry[0]["spec"] == lut.as_string() ]
      upper_bounds = np.array([ e - 1 for e in entries_available ], dtype = np.uint32)

      print ("LUTS:       ", self.__lut_list)
      print ("Num. genes: ", ngenes)
      print ("Entries:    ", entries_available)
      print ("Gene min.:  ", lower_bounds)
      print ("Gene max.:  ", upper_bounds)

      # call to the super() class initializer
      # TODO: two more parameters could be added to the constructor, to define two constraints on maximum error and minimum savings
      super().__init__(n_var = ngenes, n_obj = 2, n_constr = 0, xl = lower_bounds, xu = upper_bounds, elementwise_evaluation = True)

    """
    @brief Computes fitness and constraint values. This method is called in each iteration for each solution exactly once.

    @details
    The evaluation function _evaluate needs to be overwritten to calculated the objective and constraint values.

    @param [in]     X
                    one-dimensional NumPy array, whose number of entries equal to n_var; each element represents the
                    actual value of a variable (i.e. a gene), therefore, in the NSGA-II context, X is a chromosome

    @param [in,out] out
                    dictionary of fitness and contraints
    """
    def _evaluate(self, X, out, *args, **kwargs):
      # genotype to phenotype transition: the X chromosome is interpreteted as approximate configuration; each gene is
      # used to pick a function specification from the catalog.
      picked_entries = [ entry[gene] for gene, lut in zip(X, self.__lut_list) for entry in self.__catalog if entry[0]["spec"] == lut.as_string() ]
      #* Equavalent explanatory code
      #*for gene, lut in zip(X, self.__lut_list):
      #*  #pick the appropriate catalog entry
      #*  ax_list =  [ entry for entry in self.__catalog if entry[0]["spec"] == lut.as_string() ][0]
      #*  print ("LUT", lut.as_string(), "entries", ax_list, "gene", gene, "pick", ax_list[gene]["spec"], "gates", ax_list[gene]["gates"])

      ## Fitness evaluation
      evaluation = self.__evaluator.evaluate(picked_entries)
      # The error function: depending on the selected error metric, an appropriate evaluator should be adopted
      f1 = evaluation["error"]
      # The cost function: it is computed as the sum of the amount of AND-gates needed to synthesize the Boolean function implemented by each lut
      f2 = evaluation["cost"]

      # After doing the necessary calculations, the objective values must be added to the dictionary out with the key F
      # and the constraints with key G.
      out["F"] = [f1, f2]
      # TODO: two more functions could be added, to define two constraints on maximum error and minimum savings
      # out["G"] = [g1, g2]

  """
  @brief Constructor. Builds a new optimizer instance.

  @param [in] design      Yosys top-module instance

  @param [in] catalog     catalog of approximate LUTs.

  @param [in] nvectors    number of random test vectors for error evaluation

  @param [in] nsgaii_pop_size
              The population sized used by the algorithm.

  @param [in] nsgaii_iter
              termination criterion, defined in terms of number of generations

  @param [in] nsgaii_cross_prob
              the probability of a crossover

  @param [in] nsgaii_cross_eta
              @f$ \eta_c f@$ of crossover.  The crossover operator involves a parameter, called the distribution index 
              @f$ \eta_c f@$ which is kept fixed to a non-negative value throughout a run. If a large value of 
              @f$ \eta_c f@$ is chosen, the resulting offspring solutions are close to the parent solutions. On the
              other hand, for a small value of @f$ \eta_c f@$, solutions away from parents are likely to be created. 
              Reference: Kalyanmoy Deb, Karthik Sindhya, and Tatsuya Okabe. "Self-adaptive simulated binary crossover 
              for real-parameter optimization". In Proceedings of the 9th Annual Conference on Genetic and Evolutionary
              Computation, GECCO ‘07, 1187–1194. New York, NY, USA, 2007. ACM. 
              URL: http://doi.acm.org/10.1145/1276958.1277190, doi:10.1145/1276958.1277190.

  @param [in] nsgaii_mut_prob
              the probability of a mutation

  @param [in] nsgaii_mut_eta
              @f$ \eta_m f@$ of mutation.  The mutation operator involves a parameter, called the distribution index 
              @f$ \eta_m f@$ which is kept fixed to a non-negative value throughout a run. If a large value of 
              @f$ \eta_m f@$ is chosen, the resulting individual solutions are close to the original solutions. On the
              other hand, for a small value of @f$ \eta_m f@$, solutions away from originals are likely to be created. 
              Reference: Kalyanmoy Deb, Karthik Sindhya, and Tatsuya Okabe. "Self-adaptive simulated binary crossover 
              for real-parameter optimization". In Proceedings of the 9th Annual Conference on Genetic and Evolutionary
              Computation, GECCO ‘07, 1187–1194. New York, NY, USA, 2007. ACM. 
              URL: http://doi.acm.org/10.1145/1276958.1277190, doi:10.1145/1276958.1277190.

  @details
  In order to perform multi-objective optimization, the Optimizer class exploits the NSGA-II implementation provided by
  the pymoo module, which requires the following
    1. Implementation of a Problem (element-wise class, in our case)
    2. Initialization of an Algorithm (in our case, NSGA-II)
    3. Definition of a Termination Criterion (the number of NSGA-II generations)
    4. Optimize (minimize error and hardware requirements, in our case)
  .
  The class constructor performs the first three steps. The last one is implemepted within the optimize() method.

  """
  def __init__(self, design, catalog, n_vectors, metric, weights, nsgaii_pop_size, nsgaii_iter, nsgaii_cross_prob, nsgaii_cross_eta, nsgaii_mut_prob, nsgaii_mut_eta):
    ##* MOP definition
    #* 1. Implementation of a Problem (element-wise class, in our case)
    self.__problem = ALSOptimizer.MOP(design, catalog, ALSEvaluator(design, n_vectors, metric, weights))

    #* 2. Initialization of an Algorithm (in our case, NSGA-II)
    self.__algorithm = NSGA2(
      pop_size = nsgaii_pop_size,
      # n_offsprings = None sets the number of offsprings equal to the population size
      n_offsprings = None,
      # In the beginning, initial points need to be sampled. pymoo offers different sampling methods depending on the 
      # variable type. Here, random integers is adopted as sampling method, since genes are integer variables 
      # representing the amount of neglected bits
      sampling = get_sampling("int_random"),
      # Simulated Binary Crossover is adopted as crossover operator. Details can be found at
      # Kalyanmoy Deb, Karthik Sindhya, and Tatsuya Okabe. "Self-adaptive simulated binary crossover for real-parameter
      # optimization". In Proceedings of the 9th Annual Conference on Genetic and Evolutionary Computation, GECCO ‘07,
      # 1187–1194. New York, NY, USA, 2007. ACM. URL: http://doi.acm.org/10.1145/1276958.1277190,
      # doi:10.1145/1276958.1277190.
      crossover = get_crossover("int_sbx", prob = nsgaii_cross_prob, eta = nsgaii_cross_eta),
      # Integer mutation is adopted here. his mutation follows the same probability distribution as the simulated binary
      # crossover. Details can be found at Kalyanmoy Deb, Karthik Sindhya, and Tatsuya Okabe. "Self-adaptive simulated
      # binary crossover for real-parameter optimization". In Proceedings of the 9th Annual Conference on Genetic and
      # Evolutionary Computation, GECCO ‘07, 1187–1194. New York, NY, USA, 2007. ACM. 
      # URL: http://doi.acm.org/10.1145/1276958.1277190, doi:10.1145/1276958.1277190.
      mutation = get_mutation("int_pm", prob = nsgaii_mut_prob, eta = nsgaii_mut_eta),
      # The genetic algorithm implementation has a built in feature that eliminates duplicates after merging the parent 
      # and the offspring population. If there are duplicates with respect to the current population or in the 
      # offsprings itself they are removed and the mating process is repeated to fill up the offsprings until the 
      # desired number of unique offsprings is met.
      eliminate_duplicates = True)
    #* 3. Definition of the termination criterion
    self.__termination = get_termination('n_gen', nsgaii_iter)
    self.__result = None

  def optimize(self):
    #* 4. optimize
    self.__result = minimize(self.__problem, self.__algorithm, self.__termination, verbose = True)

  """
  @brief Print the Pareto-front resulting from DSE on a CSV file

  @param [in] report_file
              path of the CSV file
  @param [in] separator
              field separator. Default is ";"
  """
  def print_pareto(self, report_file, separator = ";"):
    original_stdout = sys.stdout
    with open(report_file, "w") as file:
      sys.stdout = file
      print("Error" + separator + "Requirements", end = "")
      # TODO: how to print LUTs on the report file?
      #for f in self.__evaluator.get_classifier().get_features():
      #  print(separator + f["name"], end = "")
      print("")
      ## Print the final population fitness and chromosome
      for fitness, chromosome in zip(self.__result.pop.get("F"), self.__result.pop.get("X")):
        for f in fitness:
          print(str(f) + separator, end="")
        for c in chromosome:
          print(str(c) + separator, end="")
        print("")
    sys.stdout = original_stdout

  """
  @brief Get the approximate configurations resulting from DSE. These will be used by the embedded coder

  @param [in] include_non_ax 
              Include the non-approximate configuration, for reference purpose. Default is True.

  @returns A list of dicts, each in the form of ... TODO
  """
  def get_axc_configurations(self, include_non_ax = True):
    ax_confs = []
    # TODO implement
    #features = self.__evaluator.get_classifier().get_features()
    #if include_non_ax:
    #  conf = []
    #  for f in features:
    #    conf.append({"name" : f["name"], "nab" : 0})
    #  ax_confs.append(conf)
    #for chromosome in self.__result.pop.get("X"):
    #  conf = []
    #  for c, f in zip(chromosome, features):
    #    conf.append({"name" : f["name"], "nab" : c})
    #  ax_confs.append(conf)
    return ax_confs
  
  def get_result(self):
    return self.__result
  
  def get_elapsed_time(self):
    return self.__result.exec_time