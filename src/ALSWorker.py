import sqlite3
from pyosys import libyosys as ys
from .ALSEpsMaxEvaluator import *
from .ALSErsEvaluator import *

class ALSWorker:
  def __init__(self, module, rewrite, luts_t, catalog, metric, weights, attempts, iterations, nvectors, debug):
    self.__module = module
    self.__rewrite = rewrite
    self.__luts_t = luts_t
    self.__catalog_db = catalog
    self.__metric = metric
    self.__iterations = iterations
    self.__weights = weights
    self.__attempts = attempts
    self.__nvectors = nvectors
    self.__debug = debug
    self.__synthesized_luts = None
    self.__db_conn = None
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
    try:
      self.__db_conn = sqlite3.connect(self.__catalog_db)
      print(sqlite3.version)

      #if self.__rewrite:
      #  self.__rewrite_run()
      #  return
      
      # 0. getting AIG
      ys.run_pass("prep",  self.__module.design)
      ys.run_pass("splitnets -ports",  self.__module.design)

      # 1. K-LUT synthesis
      ys.run_pass("synth -lut " + str(self.__luts_t), self.__module.design)
      
      # 2. SMT exact synthesis for catalog generation.
      ys.log_header(self.__module.design, "k-LUT catalog generation.\n")
      self.__catalog_generation()
      
      # 3. Optimize
      ys.log_header(self.__module.design, "Running oprimization\n")
      self.__optimize()

      ys.log_header(self.__module.design, "Rolling-back all rewrites.\n")
      ys.log_pop()
    except sqlite3.Error as e:
      print(e)
    finally:
      if self.__db_conn:
        self.__db_conn.close()

  def print_archive(self):
    # TODO: to be implemented
    pass

  def __rewrite_run(self):
    ys.log_header(self.__module.design, "Rewriting the AIG.\n")
    ys.run_pass("clean ", self.__module.design)
    to_sub = []
    for cell in self.__module.cells():
      if cell.getParam("\\LUT"):
        to_sub.append(cell)
    for cell in to_sub:
      self.__replace_lut(self.__module, cell, ALSWorker.__synthesize_lut(cell.getParam("\\LUT"), 0, self.__attempts, self.__debug, self.__db_connb))
    ys.run_pass("clean ", self.__module.design)

  def __replace_lut(self, lut, aig):
    # TODO: to be implemented
    pass

  def __catalog_generation(self):
    luts_set = {}
    for cell in self.__module.cells:
      print(cell.getParam("\\LUT"))
      luts_set.append(cell)
    pass

  def __optimize(self):
    # TODO: to be implemented
    pass

  @staticmethod
  def __synthesize_lut(lut, distance, es_max_attempts, debug, db_conn):
    # TODO: to be implemented
    pass