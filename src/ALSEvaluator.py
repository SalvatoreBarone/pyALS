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
from enum import Enum

class ALSEvaluator:
  class ErrorMetric(Enum):
    ErrorFrequency = 0,
    EpsMax = 1

  def __init__(self, design, nvectors, metric, weights):
    self.__design = design
    self.__nvectors = nvectors
    self.__metric = metric
    self.__weights = weights

  """
  @brief Implements fitness-function computation

  @param [in] configuration
              list of picked luts implementations, with corresponding required AND-gates

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