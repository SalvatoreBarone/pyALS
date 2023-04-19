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
from .ErrorMetrics import *
from .PyModelArithInt import PyModelArithInt

class ALWANNPyModelArithInt(PyModelArithInt):
    
    def __init__(self, helper, problem, signal_weights, design_name = "original"):
        PyModelArithInt.__init__(self, helper, problem, signal_weights, design_name)
        
    def get_lut_for_variant_as_mat(self, computed_circuit_outputs):
        signed        = np.min(list(self.pis_weights[0].values())) < 0 or np.min(list(self.pis_weights[1].values())) < 0 or np.min(list(self.po_weights.values())) < 0
        result        = np.zeros((2**len(self.pis_weights[0]), 2**len(self.pis_weights[1])), dtype = int)
        mapped_result = np.zeros((2**len(self.pis_weights[0]), 2**len(self.pis_weights[1])), dtype = int)
        offset_op1    = 2**(len(self.pis_weights[0])-1) if signed else 0
        offset_op2    = 2**(len(self.pis_weights[1])-1) if signed else 0

        for o in computed_circuit_outputs:
            a = int(bool_to_value({ k : i for k, i in o["i"].items() if k in self.pis_weights[0] }, self.pis_weights[0]))
            b = int(bool_to_value({ k : i for k, i in o["i"].items() if k in self.pis_weights[1] }, self.pis_weights[1]))
            r = int(bool_to_value(o["a"], self.po_weights))
            result[a + offset_op1 if signed else a][b + offset_op2 if signed else b] = r
                
        weights = range (-2**len(self.pis_weights[0]-1) if signed else 0, 2**len(self.pis_weights[0]-1)-1 if signed else 2**len(self.pis_weights[0]) )
        inputs  = range (-2**len(self.pis_weights[1]-1) if signed else 0, 2**len(self.pis_weights[1]-1)-1 if signed else 2**len(self.pis_weights[1]) )
        for w in weights:
           errors = [ np.sum( np.abs(result[w_prime + offset_op1 if signed else w_prime][i + offset_op2 if signed else i]  - w * i) for i in inputs) for w_prime in weights ]
           w_prime = np.argmin(errors)
           mapped_result[w + offset_op1 if signed else w] = result[w_prime + offset_op1 if signed else w_prime]
                    
        return mapped_result, signed, offset_op1, offset_op2