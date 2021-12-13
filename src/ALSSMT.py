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
import math, z3

class ALSSMT:
  """
  @brief Builds a new Exact-Syntesis engine for the synthesis of approximate logic.

  @param[in]  fun_spec
              Exact (non-approximate) n-input-1-output Boolean function specification to be synthesized

  @param[in]  distance
              Maximum allowed Hamming distance from the exact (non-approximate) specification in fun_spec

  @param[in]  timeout
              Timeout for the solver to circumvent time-consuming unsatisfiability trials: if an SMT problem instance 
              cannot be solved within the given time budget, the function behaves as if such a problem is unsatisfiable.
  """
  def __init__(self, fun_spec, distance, timeout):
    self.__fun_spec = fun_spec
    self.__distance = distance
    self.__solver = z3.Solver()
    self.__solver.set("timeout", timeout)
    self.__S = [[], []]       # Sets of SMT variables which represent indexes
    self.__P = [[], []]       # Sets of SMT variables which represent polarities
    self.__A = [[], []]       # Sets of SMT variables which represent login-AND gates inputs
    self.__B = []             # Set of SMT variables which represent primary input and logic-AND gates
    self.__p = z3.Bool('p')   # SMT variable for the output polarity
    self.__ax = []            # Set of SMT variable which encodes the approximate function semantic
    self.sel_var = None

  """
  @brief Generate single input assignment varying the primary-input i and the input-vector t

  @note Please kindly note that primary-inputs indexes start at 1. Input with index 0 is the constant-zero expression.

  @param [in] i primary input
  @param [in] t input vector
  """
  def __input_assignment(self, i, t):
    return False if i == 0 else bool(t & (1<<(i-1)))

  """
  @brief Add constraints to the solver context in order to encode the approximate function semantic 

  @details
  The function semantic encoded is that at least \a distance input-output correspondences of the exact behavior are 
  preserved.
  """
  def __add_ax_function_semantic_constraints(self):
    if self.__distance == 0:
      self.__solver.add( [ self.__B[-1][t] == z3.Xor(False if self.__fun_spec[t] == "0" else True, z3.Not(self.__p)) for t in range(len(self.__fun_spec)) ] )
      self.__ax = [False for i in range(len(self.__fun_spec)) ]
    else:
      self.__ax = [z3.Bool("ax_{t}".format(t = t )) for t in range(len(self.__fun_spec))]
      self.__solver.add( [ self.__ax[t] == z3.Xor(self.__B[-1][t], (z3.Xor(z3.Not(self.__p), False if self.__fun_spec[t] == "0" else True))) for t in range(len(self.__fun_spec)) ])
      self.__solver.add(z3.AtMost(*self.__ax, self.__distance))

  """
  @brief Get the synthetisez function specification, as a string
  """
  def __get_synthesized_spec(self):
    if self.__distance > 0:
      original_spec = [ True if self.__fun_spec[i] == "1" else False for i in range(len(self.__fun_spec)) ]
      smt_result = [ self.__solver.model()[self.__ax[i]] for i in range(len(self.__fun_spec)) ]
      final_spec = [ bool(original_spec[i]) != bool(smt_result[i]) for i in range(len(self.__fun_spec)) ]
    return "".join(["1" if bool(final_spec[i]) else "0" for i in range(len(self.__fun_spec))]) if self.__distance > 0 else self.__fun_spec

  """
  @brief Perform the exact synthesis of a given n-input-1-output Boolean function, using the SMT formulation.

  @param[in] fun_spec
            Exact (non-approximate) n-input-1-output Boolean function specification to be synthesized

  @param[in] distance
            Maximum allowed Hamming distance from the exact (non-approximate) specification in fun_spec

  @param[in] timeout
            Timeout for the solver to circumvent time-consuming unsatisfiability trials: if an SMT problem instance 
            cannot be solved within the given time budget, the function behaves as if such a problem is unsatisfiable.

  @returns  the synthesized specification and its corresponding number of AND-gates
  """
  def synthesize(self):
    num_inputs = math.ceil(math.log2(len(self.__fun_spec)))
    assert 2**num_inputs == len(self.__fun_spec), "Incomplete specification"
    self.__S = [[], []]       # Sets of SMT variables which represent indexes
    self.__P = [[], []]       # Sets of SMT variables which represent polarities
    self.__A = [[], []]       # Sets of SMT variables which represent login-AND gates inputs
    self.__B = []            # Set of SMT variables which represent primary input and logic-AND gates
    self.__p = z3.Bool('p')  # SMT variable for the output polarity
    self.__ax = []           # Set of SMT variable which encodes the approximate function semantic

    self.sel_var = single_var(self.__fun_spec, self.__distance)
    if self.sel_var is not None:
        self.sel_out = int(self.sel_var / 2)
        self.sel_out_p = self.sel_var % 2 == 0
        sel_fun_spec = truth_table_column(self.sel_out, num_inputs, self.sel_out_p)
        return "".join(["1" if bool(sel_fun_spec[i]) else "0" for i in range(len(self.__fun_spec))]), [[], []], [[], []], self.sel_out_p, self.sel_out

    #* Input assignment
    #* This formulation makes use of the explicit function representation -- i.e. the Boolean function is represented in 
    #* terms of truth table values, for each of the possible 2^n input assignments. Moreover, in order to encode the 
    #* behavior of the Boolean function for each input assignment, each node i [n+1, n+r] is replicated once for each of
    #* the input vectors t in [0, 2^n-1].
    # Set of SMT variables which encode primary-inputs assignment for t in [0 2**ninputs-1], for i in [0 ninputs]
    self.__B = [ [ z3.Bool("b_{i}_{t}".format(i = i, t = t)) for t in range(len(self.__fun_spec)) ] for i in range(num_inputs + 1) ] 
    self.__solver.add([ self.__B[i][t] == self.__input_assignment(i, t) for i in range(num_inputs + 1) for t in range(len(self.__fun_spec)) ])

    self.__solver.push() # Create a backtracking point
    # Encode the function semantic
    self.__add_ax_function_semantic_constraints()

    #* The first time the z3.Solver.check() function is called, no element has yet been added in B that encodes the 
    #* logic-AND behavior, so it is as if synthesis is attempted with zero nodes, i.e. using a constant value.
    while self.__solver.check() != z3.sat:
      nodes = len(self.__B)
      gates = nodes - num_inputs - 1
      # Go to the last backtraking point. This effectively brings back the solver as if the check() function has not yet
      # been called, and removes constraints added by the previous call to the add_ax_function_semantic_constraints()
      # function. In this way we can add further constraints before we call check() again.
      self.__solver.pop()

      #* 1. introduce s_1_i and s_2_i indexes, and  p_1_i and p_2_i boolean variables, for i in [n+1, n+r] and 2. enforce
      #* no-cycles and ordering constraints, i.e. s_1i < s_2i < i for i in [n+1, n+r] 
      for c in range(2):
        self.__S[c].append(z3.Int("s_{}_{}".format(c,nodes)))
        self.__P[c].append(z3.Bool("p_{}_{}".format(c, nodes)))
        self.__solver.add(self.__S[c][gates] < nodes, self.__S[c][gates] >= 0)
      self.__solver.add(self.__S[0][gates] < self.__S[1][gates])

      #* 3. encode the logic-AND behavior, i.e. b_i^(t) = a_1_i^(t) & a_2_i^(t),for i in [n+1, n+r], t in [0, 2**n-1], and 
      self.__B.append([z3.Bool("b_{i}_{t}".format(i = nodes, t = t)) for t in range(len(self.__fun_spec))])
      for c in range(2):
        self.__A[c].append([z3.Bool("a_{c}_{i}_{t}".format(c = c, i = nodes, t = t)) for t in range(len(self.__fun_spec))])
      self.__solver.add( [ self.__B[nodes][t] == z3.And(self.__A[0][gates][t], self.__A[1][gates][t]) for t in range(len(self.__fun_spec)) ] )
      #* 4. encode primary-input connection and value propagation
      self.__solver.add( [ z3.Implies(self.__S[c][gates] == j, self.__A[c][gates][t] == z3.Xor(self.__B[j][t], z3.Not(self.__P[c][gates]))) for c in range(2) for j in range(nodes) for t in range(len(self.__fun_spec)) ])

      self.__solver.push() # Create a backtracking point
      #* 5. Encode the function semantic
      self.__add_ax_function_semantic_constraints()

    model = self.__solver.model()
    S = [ [ model[s].as_long() for s in self.__S[0] ], [ model[s].as_long() for s in self.__S[1] ] ]
    P = [ [ 1 if model[p] else 0 for p in self.__P[0] ], [ 1 if model[p] else 0 for p in self.__P[1] ] ]
    p = 1 if model[self.__p] else 0
    return self.__get_synthesized_spec(), S, P, p, 0

def hamming(s1, s2):
  result = 0
  if len(s1) == len(s2):
    for x, (i, j) in enumerate(zip(s1, s2)):
      if i != j:
        result += 1
  return result


def truth_table_value(i, t):
  if i == 0:
    return False
  return t % (1 << i) >= (1 << (i - 1))


def truth_table_column(i, num_vars, p):
  bs = [False] * (1 << num_vars)
  for t in range(len(bs)):
    bs[t] = truth_table_value(i, t) == p
  return bs


def single_var(fun_spec, out_distance):
  num_vars = math.ceil(math.log2(len(fun_spec)))
  fun_spec = [True if c == "1" else False for c in fun_spec]
  for i in range(num_vars + 1):
    if hamming(fun_spec, truth_table_column(i, num_vars, True)) <= out_distance:
      return i * 2
    elif hamming(fun_spec, truth_table_column(i, num_vars, False)) <= out_distance:
      return (i * 2) + 1
  return None