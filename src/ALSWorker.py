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
from pyosys import libyosys as ys

from .ALSCatalog import *
from .ALSOptimizer import *

class ALSWorker:
  """
  @param Builds a new Als-worker.

  @param [in] module      Yosys top-module instance
  @param [in] luts_tech   LUT technology to be adopted (4-LUT, 6-LUT...)
  @param [in] catalog     path to the catalog.
  @param [in] es_timeout  time budget for the SMT synthesis of LUTs, in ms.
  @param [in] nvectors    number of random test vectors for error evaluation
  @param [in] metric      error metric (ers, epsmax)
  @param [in] weights     weights for the output signals
  @param [in] popsize     NSGA-II population size
  @param [in] iter        NSGA-II termination criterion, in terms of iterations.
  @param [in] pcross      NSGA-II crossover probability
  @param [in] etac        NSGA-II crossover distribution index
  @param [in] pmut        NSGA-II mutation probability
  @param [in] etam        NSGA-II mutation distribution index
  """
  def __init__(self, module, luts_tech, catalog, es_timeout, nvectors, metric, weights, popsize, iter, pcross, etac, pmut, etam):
    self.__module = module
    self.__luts_tech = luts_tech
    self.__catalog = ALSCatalog(catalog, es_timeout)
    self.__nvectors = nvectors
    self.__metric = metric
    self.__weights = weights
    self.__popsize = popsize
    self.__iter = iter
    self.__pcross = pcross
    self.__etac = etac
    self.__pmut = pmut
    self.__etam = etam

    if self.__metric == "ers":
      self.__metric == ALSEvaluator.ErrorMetric.ErrorFrequency
    else:
      print("Unrecognized error metric. Bailing out!")
      sys.exit(0)
    
  """
  @brief Implements the whole Catalog-based AIG rewriting (C-AIGRW) approximate technique workflow

  @details
  Briefly, the general idea behind C-AIGRW is to enumerate k-feasible cuts for a given AIG, and, then, supersede
  carefully selected cuts with similar ones, exhibiting better performances, exploit partial cut-enumeration algorithms,
  which are effectively adopted for FPGA synthesis in order to compute the graph of interconnected k-cuts or,
  alternatively, interconnected k-LUTs.

  Thus, for each unique k-cut @f$c \in C$, we generate a catalog of approximate cuts, each of which is an approximate
  Boolean function at a predetermined Hamming distance from the considered cut. Approximate variants' generation for $C$
  take place by substituting a given cut -- or, alternatively, a LUT instance -- using one of its approximate variants,
  picked from the catalog, and rewriting back the corresponding AIG.
  
  The relationship between an AIG size, in terms of both depth and number of nodes, and its hardware requirements in
  terms of critical path and cells suggests that whether the approximate circuit consists of fewer nodes, then its
  hardware requirements will be lower than the original circuit.
  """
  def run(self):
      #if self.__rewrite:
      #  self.__rewrite_run()
      #  return
      
      # 0. getting AIG
      ys.run_pass("prep",  self.__module.design)
      ys.run_pass("splitnets -ports",  self.__module.design)

      # 1. K-LUT synthesis
      ys.run_pass("synth -lut " + str(self.__luts_tech), self.__module.design)
      ys.run_pass("show", self.__module.design)      

      # 2. SMT exact synthesis for catalog generation.
      ys.log_header(self.__module.design, "k-LUT catalog generation.\n")
      catalog_entries = self.__catalog.generate_catalog(self.__module.design)

      # 3. Optimization
      ys.log_header(self.__module.design, "Running oprimization\n")
      ys.log_push()
      optimizer = ALSOptimizer(self.__module.design, catalog_entries, self.__nvectors, self.__metric, self.__weights, self.__popsize, self.__iter, self.__pcross, self.__etac, self.__pmut, self.__etam)
      optimizer.optimize()
      optimizer.print_pareto()
      ys.log_pop()

      ys.log_header(self.__module.design, "Rolling-back all rewrites.\n")
      ys.log_pop()
    
