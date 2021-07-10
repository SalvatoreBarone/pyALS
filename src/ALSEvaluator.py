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
import igraph as ig
from enum import Enum
from pyosys import libyosys as ys
from .ALSGraph import *

class ALSEvaluator:
  class ErrorMetric(Enum):
    ErrorFrequency = 0,
    EpsMax = 1

  def __init__(self, design, nvectors, metric, weights):
    self.__metric = self.__parse_metric(metric)
    self.__graph = ALSGraph(design, weights)
    self.__test_vectors = self.__graph.generate_random_test_set(nvectors)
    ys.log_header(design, "Collecting the circuit outputs...\n")
    self.__expected_outputs = [ self.__graph.evaluate(t) for t in self.__test_vectors]

  """
  @brief Implements fitness-function computation

  @param [in] configuration
              list of picked luts implementations, with corresponding required AND-gates. The list MUST be in the 
              following form:
              [
                {"name" : lut_name, "spec" : lut_spec, "gates" : AND_gates},
                {"name" : lut_name, "spec" : lut_spec, "gates" : AND_gates},
                ...
                {"name" : lut_name, "spec" : lut_spec, "gates" : AND_gates},
              ]

  @return a dict containing both the error and the cost fitness function values for the given configuration
  """
  def evaluate(self, configuration):
    return {"error" : self.__compute_error(configuration), "cost" : self.__compute_requirements(configuration)}

  """
  @brief Computes the error function, depending on the selected error metric

  @param [in] configuration
              list of picked luts implementations, with corresponding required AND-gates

  @details 
  The cost function is computed as the sum of the amount of AND-gates needed to synthesize the Boolean function 
  implemented by each of the picked luts
  """
  def __compute_error(self, configuration):
    outputs = [ self.__graph.evaluate(t, configuration) for t in self.__test_vectors]
    if self.__metric == ALSEvaluator.ErrorMetric.ErrorFrequency:
      return sum ([ 1 if e != o else 0 for e, o in zip(self.__expected_outputs, outputs) ]) / len(self.__expected_outputs)
    elif self.__metric == ALSEvaluator.ErrorMetric.EpsMax:
      weights = self.__graph.get_po_weights()
      return max([ sum([w if e[i] != o[i] else 0 for i in range(zip(e,o))]) for e, o, w in zip(self.__expected_outputs, outputs, weights) ])
    else:
      return 0

  """
  @brief Compute the cost function.

  @param [in] configuration
              list of picked luts implementations, with corresponding required AND-gates

  @details 
  The cost function is computed as the sum of the amount of AND-gates needed to synthesize the Boolean function 
  implemented by each of the picked luts
  """
  def __compute_requirements(self, configuration):
    return sum ([ e["gates"] for e in configuration])  

  def __parse_metric(self, metric):
    if metric == "ers":
      return ALSEvaluator.ErrorMetric.ErrorFrequency
    elif metric == "epsmax":
      return ALSEvaluator.ErrorMetric.EpsMax
    else:
      # TODO raise an exception
      pass