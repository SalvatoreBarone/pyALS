"""
Copyright 2021-2025 Salvatore Barone <salvatore.barone@unina.it>

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
from .ErrorMetrics import *
from .PyModelArithInt import PyModelArithInt
from tqdm import tqdm

class ALWANNPyModelArithInt(PyModelArithInt):
    
    def __init__(self, helper, problem, signal_weights, design_name = "original"):
        PyModelArithInt.__init__(self, helper, problem, signal_weights, design_name)
        
    def get_lut_for_variant_as_mat(self, computed_circuit_outputs):
        behavioral_model, signed, offset_op1, offset_op2 = PyModelArithInt.get_lut_for_variant_as_mat(self, computed_circuit_outputs)
        alwann_behavior  = np.zeros((2**len(self.pis_weights[0]), 2**len(self.pis_weights[1])), dtype = int)        
        weights = range (-2**(len(self.pis_weights[0])-1) if signed else 0, 2**(len(self.pis_weights[0])-1) if signed else 2**len(self.pis_weights[0]) )
        inputs  = range (-2**(len(self.pis_weights[1])-1) if signed else 0, 2**(len(self.pis_weights[1])-1) if signed else 2**len(self.pis_weights[1]) )
        for w in tqdm(weights, desc = "Performing weight tuning...", leave = False, bar_format="{desc:40} {percentage:3.0f}% |{bar:60}{r_bar}{bar:-10b}"):
            errors = [ np.sum([np.abs(behavioral_model[w_prime + offset_op1 if signed else w_prime][i + offset_op2 if signed else i]  - w * i) for i in inputs ]) for w_prime in weights ]
            w_prime = np.argmin(errors) - offset_op1 if signed else 0
            alwann_behavior[w + offset_op1 if signed else w] = np.copy(behavioral_model[w_prime + offset_op1 if signed else w_prime])
            assert np.array_equal(alwann_behavior[w + offset_op1 if signed else w], behavioral_model[w_prime + offset_op1 if signed else w_prime])
            assert alwann_behavior[w + offset_op1 if signed else w] is not behavioral_model[w_prime + offset_op1 if signed else w_prime]
        return alwann_behavior, signed, offset_op1, offset_op2
    
    def get_shifted_lut_for_variant_as_mat(self, computed_circuit_outputs, ishift, oshift):
        behavioral_model, signed, offset_op1, offset_op2 = PyModelArithInt.get_shifted_lut_for_variant_as_mat(self, computed_circuit_outputs, ishift, oshift)
        alwann_behavior  = np.zeros((2**(len(self.pis_weights[0]) + ishift), 2**len(self.pis_weights[1]) + ishift), dtype = int)
        weights = range (-2**(len(self.pis_weights[0])+ishift-1) if signed else 0, 2**(len(self.pis_weights[0])+ishift-1) if signed else 2**(len(self.pis_weights[0])+ishift) )
        inputs  = range (-2**(len(self.pis_weights[1])+ishift-1) if signed else 0, 2**(len(self.pis_weights[1])+ishift-1) if signed else 2**(len(self.pis_weights[1])+ishift) )
        for w in tqdm(weights, desc = "Performing weight tuning...", leave = False, bar_format="{desc:40} {percentage:3.0f}% |{bar:60}{r_bar}{bar:-10b}"):
            errors = [ np.sum([np.abs(behavioral_model[w_prime + offset_op1 if signed else w_prime][i + offset_op2 if signed else i]  - w * i) for i in inputs ]) for w_prime in weights ]
            w_prime = np.argmin(errors) - offset_op1 if signed else 0
            alwann_behavior[w + offset_op1 if signed else w] = np.copy(behavioral_model[w_prime + offset_op1 if signed else w_prime])
            assert np.array_equal(alwann_behavior[w + offset_op1 if signed else w], behavioral_model[w_prime + offset_op1 if signed else w_prime])
            assert alwann_behavior[w + offset_op1 if signed else w] is not behavioral_model[w_prime + offset_op1 if signed else w_prime]
        return alwann_behavior, signed, offset_op1, offset_op2
        
