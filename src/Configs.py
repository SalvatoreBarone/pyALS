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

class ALSConfig:
    def __init__(self, luttech, catalog, timeout):
        self.luttech = luttech
        self.catalog = catalog
        self.timeout = timeout

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

class AMOSAConfig:
    def __init__(
            self,
            archive_hard_limit,
            archive_soft_limit,
            archive_gamma,
            hill_climbing_iterations,
            initial_temperature,
            final_temperature,
            cooling_factor,
            annealing_iterations):
        self.archive_hard_limit = archive_hard_limit
        self.archive_soft_limit = archive_soft_limit
        self.archive_gamma = archive_gamma
        self.hill_climbing_iterations = hill_climbing_iterations
        self.initial_temperature = initial_temperature
        self.final_temperature = final_temperature
        self.cooling_factor = cooling_factor
        self.annealing_iterations = annealing_iterations
