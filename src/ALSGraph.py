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
import random
import igraph as ig
from igraph import layout
from pymoo.problems.many.wfg import correct_to_01
from pyosys import libyosys as ys
from enum import Enum

class ALSGraph:
  class VertexType(Enum):
    CONSTANT_ZERO = 0, 
    CONSTANT_ONE = 1, 
    PRIMARY_INPUT = 2, 
    CELL = 3,
    PRIMARY_OUTPUT = 4

  def __init__(self, design, weights):
    self.__design = design
    self.__weights = weights
    self.__graph = ig.Graph(directed=True)
    self.__graph_from_design()
    self.__graph.vs["label"] = self.__graph.vs["name"]
    self.__pinputs = [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.PRIMARY_INPUT]
    self.__const0 = [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.CONSTANT_ZERO]
    self.__const1 = [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.CONSTANT_ONE]
    self.__cells = [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.CELL]
    self.__poutputs = [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.PRIMARY_OUTPUT]

  def get_po_weights(self):
    return [v["weight"] for v in self.__poutputs ]

  def generate_random_test_set(self, nvectors):
    return [ [ bool(random.getrandbits(1)) for n in range(len(self.__pinputs)) ] for i in range(nvectors) ]

  """
  @brief Evaluate the circuit output, using its graph representation

  @param [in] inputs
              circuit inputs: a list of Boolean elements.

  @param [in] configuration
              Approximate configuration: list of picked luts implementations, with corresponding required AND-gates. 
              The list MUST be in the 
              following form:
              [
                {"name" : lut_name, "spec" : lut_spec, "gates" : AND_gates},
                {"name" : lut_name, "spec" : lut_spec, "gates" : AND_gates},
                ...
                {"name" : lut_name, "spec" : lut_spec, "gates" : AND_gates},
              ]
  """
  def evaluate(self, inputs, configuration = None):
    cell_values = dict()
    #* assign an appropriate value to constants  
    for c in self.__const0:
      cell_values[c] = False
    for c in self.__const1:
      cell_values[c] = True
    #* assign a value to each primary input
    assert len(self.__pinputs) == len(inputs)
    for p, i in zip (self.__pinputs, inputs):
      cell_values[p] = bool(i)
    #* evaluate the output of each cell
    for c in self.__cells:
      input_value = [ cell_values[n] for n in c.neighbors(mode="in") ]
      out_idx = sum ([ 1 * 2** i if input_value[i] else 0 for i in range(len(input_value)) ])
      cell_spec = None
      if configuration == None:
        cell_spec = c["cell"].parameters[ys.IdString("\LUT")].as_string()[::-1] 
      else:
        #*get the element of the list having the appropriate spec
        cell_spec = [ conf for conf in configuration if conf["name"] == c["name"] ][0]["spec"][::-1]
        #print("Ax spec:", cell_spec)
      out_value = cell_spec[out_idx]
      #print("{name} {spec} [{n}] = {i} ({I}) -> {o}".format(name = c["name"], spec = cell_spec, n = [ n["name"] for n in c.neighbors(mode="in") ],  i = input_value, I = out_idx, o = out_value))
      cell_values[c] = True if out_value == "1" else False
    #* evaluate the circuit output
    output = []
    for o in self.__poutputs:
      cell_values[o] = cell_values[c.neighbors(mode="in")[0]]
      #print("{name} -> {o}".format(name = o["name"], o = cell_values[o]))
      output.append(cell_values[o])
    #print(output)
    return output

  def plot(self):
    layout = self.__graph.layout("kk")
    ig.plot(self.__graph, layout = layout)

  """
  @brief Parse the design to build a local representation of the circuit, which will be employed to evaluate the output of the latter, given an input
  """
  def __graph_from_design(self):
    # In Yosys it is very easy to go from cells to wires but hard to go in the other way. The solution is easy: create 
    # a custom indexes that allow you to make fast lookups for the wire-to-cell direction...
    driver_of = dict()
    #* Builds up a new vertex for each LUT in the circuit graph. 
    #* In addition, it keeps track of wires connected to each cell.
    for module in self.__design.selected_whole_modules_warn():
      sigmap = ys.SigMap(module) #! take a look at the line above the driver_of definition!
      for cell in module.selected_cells():
        self.__add_cell_vertex(cell)
        self.__collect_driven_signals(cell, sigmap, driver_of)
    #* Add driver-driven edges between cells, primary-inputs and constants
    constant_one_vertex = None
    constant_zero_vertex = None
    for module in self.__design.selected_whole_modules_warn():
      sigmap = ys.SigMap(module)
      for cell in module.selected_cells():
        connection_index = 0
        cell_index = self.__graph.vs.find(name = cell.name.str()).index
        A = cell.connections_[ys.IdString("\A")]
        Y = cell.connections_[ys.IdString("\Y")]
        if cell.input(ys.IdString("\A")):
          signal_index = 0
          for sig in sigmap(A).to_sigbit_set():
            #* if the signal is in the driver_of dict, then it is driven by some cell; it can be either an intermediate signal or a primary output
            #* Nevertheless, primary outputs are not added to the graph
            if sig in driver_of:
              #* search for the index of the vertex named as sig.wire.name.str() in the list of vertices, if any
              vertex = self.__graph.vs.find(name = driver_of[sig]["cell"].name.str()).index
              self.__graph.add_edges([(vertex, cell_index)])
              #print("adding the {} -> {} connection".format(driver_of[sig]["cell"].name.str(), cell.name.str()))
            elif sig.wire: #* sig is a primary input
              #* search for the index of the vertex named as sig.wire.name.str() in the list of vertices, if any
              vertex = [v for v in range(len(self.__graph.vs)) if self.__graph.vs[v]["name"] == sig.wire.name.str()]
              if not bool(vertex): vertex = self.__add_PI_vertex(sig)
              else: vertex = vertex[0]
              self.__graph.add_edges([(vertex, cell_index)])
              #print("Adding {} -> {}".format(sig.wire.name.str(), cell.name.str()))
            elif sig.data == ys.State.S1: #* sig is the constant one
              if constant_one_vertex is None: #* if no constant one node has been created yet, it is added to the graph
                constant_one_vertex = self.__add_C1_vertex(sig)
              self.__graph.add_edges([(constant_one_vertex, cell_index)])
              #print("Adding {} -> {}".format(sig.wire.name.str(), cell.name.str()))
            elif sig.data == ys.State.S0: #* sig is the constant zero
              if constant_zero_vertex is None: #* if no constant one node has been created yet, it is added to the graph
                constant_zero_vertex = self.__add_C0_vertex(sig)
              self.__graph.add_edges([(constant_zero_vertex, cell_index)])
              #print("Adding {} -> {}".format(sig.wire.name.str(), cell.name.str()))
            self.__graph.es[-1]["c"] = connection_index
            self.__graph.es[-1]["s"] = signal_index
            signal_index += 1
        connection_index += 1
  
  """
  @brief add a CELL vertex to the graph

  @return The vertex index
  """
  def __add_cell_vertex(self, cell):
    self.__graph.add_vertex()
    self.__graph.vs[-1]["type"] = ALSGraph.VertexType.CELL
    self.__graph.vs[-1]["name"] = cell.name.str()
    self.__graph.vs[-1]["hash"] = cell.name.hash()
    self.__graph.vs[-1]["cell"] = cell
    self.__graph.vs[-1]["weight"] = None
    A = cell.connections_[ys.IdString("\A")]
    Y = cell.connections_[ys.IdString("\Y")]
    #* check whether the output signal is a wire. This means the output signal is a primary output.
    current_vertex = len( self.__graph.vs) - 1
    if Y.is_wire():
      po_idx = self.__add_PO_vertex(Y.as_bit().wire)
      self.__graph.add_edges([(current_vertex, po_idx)])
    return current_vertex

  """
  @brief collect signals driven from the given cell in the dict_of_driven_signals dictionary
  """
  def __collect_driven_signals(self, cell, sigmap, dict_of_driven_signals):
    Y = cell.connections_[ys.IdString("\Y")]
    if cell.output(ys.IdString("\Y")):
      for sig in sigmap(Y).to_sigbit_set():
        dict_of_driven_signals[sig] = { "vertex_i" : len(self.__graph.vs) - 1, "cell" : cell }
        #print("{} is driven by {}".format(sig.wire.name.str(), cell.name.str()))

  """
  @brief add a PI vertex to the graph

  @return The vertex index
  """
  def __add_PI_vertex(self, input_signal):
    self.__graph.add_vertex()
    self.__graph.vs[-1]["type"] = ALSGraph.VertexType.PRIMARY_INPUT
    self.__graph.vs[-1]["name"] = input_signal.wire.name.str()
    self.__graph.vs[-1]["hash"] = input_signal.wire.name.hash()
    self.__graph.vs[-1]["cell"] = None
    self.__graph.vs[-1]["weight"] = None
    return len( self.__graph.vs) - 1

  """
  @brief add a constant one vertex to the graph

  @return The vertex index
  """
  def __add_C1_vertex(self, input_signal):
    self.__graph.add_vertex()
    self.__graph.vs[-1]["type"] = ALSGraph.VertexType.CONSTANT_ONE
    self.__graph.vs[-1]["name"] = input_signal.wire.name.str()
    self.__graph.vs[-1]["hash"] = input_signal.wire.name.hash()
    self.__graph.vs[-1]["cell"] = None
    self.__graph.vs[-1]["weight"] = None
    return len( self.__graph.vs) - 1

  """
  @brief add a constant zero vertex to the graph

  @return The vertex index
  """
  def __add_C0_vertex(self, input_signal):
    self.__graph.add_vertex()
    self.__graph.vs[-1]["type"] = ALSGraph.VertexType.CONSTANT_ZERO
    self.__graph.vs[-1]["name"] = input_signal.wire.name.str()
    self.__graph.vs[-1]["hash"] = input_signal.wire.name.hash()
    self.__graph.vs[-1]["cell"] = None
    self.__graph.vs[-1]["weight"] = None
    return len( self.__graph.vs) - 1

  """
  @brief add a PO vertex to the graph

  @return The vertex index
  """
  def __add_PO_vertex(self, signal):
    self.__graph.add_vertex()
    self.__graph.vs[-1]["type"] = ALSGraph.VertexType.PRIMARY_OUTPUT
    self.__graph.vs[-1]["name"] = signal.name.str()
    self.__graph.vs[-1]["hash"] = signal.name.hash()
    self.__graph.vs[-1]["cell"] = None
    self.__graph.vs[-1]["weight"] = None
    #* check whether there is a weight specification for the signal
    if self.__weights:
      #* search for the cell name in the weights list, in order to get the corresponding weight
      weight_spec = [ i for i in self.__weights if i[0] == signal.name.str().replace("\\","") ]
      if bool(weight_spec): #* if the list is not empty, i.e. there is a weight specification for the signal...
        self.__graph.vs[-1]["weight"] = 2**int(weight_spec[0][1]) #* we pick the weight field (as an integer). Note the weight is converted in power of two.
      else: #* partial weights specification is not allowed
        # TODO raise an exception
        pass
    return len( self.__graph.vs) - 1