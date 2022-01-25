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
import copy
import igraph as ig
from pyosys import libyosys as ys
from enum import Enum

class ALSGraph:
  class VertexType(Enum):
    CONSTANT_ZERO = 0, 
    CONSTANT_ONE = 1, 
    PRIMARY_INPUT = 2, 
    CELL = 3,
    PRIMARY_OUTPUT = 4

  def __init__(self, design = None):
    if design:
      self.__graph = ig.Graph(directed=True)
      self.__graph_from_design(design)
      self.__graph.vs["label"] = self.__graph.vs["name"]
    else:
      self.__graph = None

  def __deepcopy__(self, memo = None):
    graph = ALSGraph()
    graph.__graph = copy.deepcopy(self.__graph)
    return graph 

  def get_pi(self):
    return [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.PRIMARY_INPUT]

  def get_po(self):
    return [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.PRIMARY_OUTPUT]

  def get_cells(self):
    return [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.CELL]
    
  def get_num_cells(self):
    return len([v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.CELL])

  def get_depth(self, configuration):
    top_ord = self.__graph.topological_sorting()
    depths = [0] * len(top_ord)

    for i, v in zip(range(len(top_ord)), [self.__graph.vs[v_i] for v_i in top_ord]):
      if v["type"] in (ALSGraph.VertexType.CELL, ALSGraph.VertexType.PRIMARY_OUTPUT):
        depths[i] = max((configuration[p["name"]]["depth"] if p["type"] == ALSGraph.VertexType.CELL else 0) for p in v.predecessors()) + (configuration[v["name"]]["depth"] if v["type"] == ALSGraph.VertexType.CELL else 0)

    return max(depths)

  """
  @brief Evaluate the circuit output, using its graph representation

  @param [in] inputs
              circuit inputs: it must be a dict assigning a Boolean values to each primary-input

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

  @return the circuit output vector, i.e. a list of Boolean values, each corresponding to a primary-output
  """
  def evaluate(self, inputs, configuration = None):
    cell_values = dict()
    for c in [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.CONSTANT_ZERO]:
      cell_values[c] = False
    for c in [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.CONSTANT_ONE]:
      cell_values[c] = True
    for p in [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.PRIMARY_INPUT]:
      cell_values[p] = inputs[p["name"]]
    for cell in [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.CELL]:
      self.__evaluate_cell_output(cell_values, cell, configuration)
    output = dict()
    for o in [v for v in self.__graph.vs if v["type"] == ALSGraph.VertexType.PRIMARY_OUTPUT]:
      cell_values[o] = cell_values[o.neighbors(mode="in")[0]]
      output[o["name"]] = cell_values[o]
    return output

  """
  @brief Evaluate the output of a cell.

  @param [in, out] cell_values
                   a cell-indexed dictionary, which, for each cell, the current cell output is specified

  @param [in] c
              a cell of the circuit (a vertex of the graph)

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
  def __evaluate_cell_output(self, cell_values, cell, configuration):
    input_values = []
    input_names = []
    for n in cell["in"]:
      input_names.append(self.__graph.vs[n]["name"])
      if self.__graph.vs[n] in cell_values:
        input_values.append(cell_values[self.__graph.vs[n]])
      else:
        input_values.append(self.__evaluate_cell_output(cell_values, self.__graph.vs[n], configuration))
    out_idx = sum ([ 1 * 2** i if input_values[i] else 0 for i in range(len(input_values)) ])
    out_value = cell["spec"][out_idx]
    if configuration == None:
      cell_values[cell] = True if out_value == "1" else False
    else:
      cell_conf = configuration[cell["name"]]
      cell_values[cell] = True if cell_conf["axspec"][out_idx] == "1" else False
    #print("name: {name} Spec: {spec}, Dist.: {dist}, AxSpec: {axspec}, Inputs: {inputs} = {I} (Index: {i}) -> Output: {o} ({O}) AxOutput: {axo})".format(name = cell["name"], spec = cell_spec, dist = dist, axspec = ax_cell_spec, inputs = input_names, I = input_values, i = out_idx, o=out_value, O = cell_values[cell], axo =  ax_out_value))
    return cell_values[cell]

  def plot(self):
    layout = self.__graph.layout("sugiyama")
    layout.rotate(270)
    ig.plot(self.__graph, layout = layout, bbox=(2000, 2000), margin=120, hovermode='closest', vertex_label_dist = 1)

  def __graph_from_design(self, design):
    driver_of = dict()
    self.__add_PI_and_PO_to_graph(design)
    self.__look_for_direct_PI_to_PO_connections(design)
    self.__add_LUTs_to_graph(design, driver_of)
    self.__interconnect_cells(design, driver_of)
  
  def __add_PI_and_PO_to_graph(self, design):
    for module in design.selected_whole_modules_warn():
      for wire in module.selected_wires():
        if (wire.port_input): # the wire is a primary input
         self.__add_PI_vertex(wire)
        if (wire.port_output): # the wire is a primary output
          self.__add_PO_vertex(wire)

  def __look_for_direct_PI_to_PO_connections(self, design):
    for module in design.selected_whole_modules_warn():
      sigmap = ys.SigMap(module) # take a look at the line above the driver_of definition!
      for wire in module.selected_wires():
        for sig in sigmap(wire).to_sigbit_vector():
          if sig.is_wire():
            if sig.wire.name.str() != wire.name.str():
              pi_index = self.__add_PI_vertex(sig.wire)
              po_index = self.__add_PO_vertex(wire)
              #print("Adding direct connection {source_wire} -> {sink_wire}".format(source_wire=sig.wire.name.str() , sink_wire=wire.name.str()))
              self.__graph.add_edges([(pi_index, po_index)])
              self.__graph.vs[po_index]["in"].append(pi_index)
          else:
            if sig.data == ys.State.S0:
              const_0 = self.__add_C0_vertex()
              po_index = self.__add_PO_vertex(wire)
              #print("Adding direct connection {source_wire} -> {sink_wire}".format(source_wire="C_0" , sink_wire=wire.name.str()))
              self.__graph.add_edges([(const_0, po_index)])
              self.__graph.vs[po_index]["in"].append(const_0)
            elif sig.data == ys.State.S1:
              const_1 = self.__add_C1_vertex()
              po_index = self.__add_PO_vertex(wire)
              #print("Adding direct connection {source_wire} -> {sink_wire}".format(source_wire="C_1" , sink_wire=wire.name.str()))
              self.__graph.add_edges([(const_1, po_index)])
              self.__graph.vs[po_index]["in"].append(const_1)

  def __add_LUTs_to_graph(self, design, driver_of):
    for module in design.selected_whole_modules_warn():
      sigmap = ys.SigMap(module)
      for cell in module.selected_cells():
        self.__add_cell_vertex(cell)
        self.__collect_signals_driven_by_cell(cell, sigmap, driver_of)

  def __interconnect_cells(self, design, driver_of):
    #* Add driver-driven edges between cells, primary-inputs and constants
    for module in design.selected_whole_modules_warn():
      sigmap = ys.SigMap(module)
      for cell in module.selected_cells():
        cell_index = self.__add_cell_vertex(cell)
        A = cell.connections_[ys.IdString("\A")]
        Y = cell.connections_[ys.IdString("\Y")]
        if cell.input(ys.IdString("\A")):
          for sig in sigmap(A).to_sigbit_vector():
            #* if the signal is in the driver_of dict, then it is driven by some cell; it can be either an intermediate signal or a primary output
            if sig in driver_of:
              #* search for the index of the vertex named as sig.wire.name.str() in the list of vertices
              vertex = self.__graph.vs.find(name = driver_of[sig]["cell"].name.str()).index
              #* and adds the connecting edge
              self.__graph.add_edges([(vertex, cell_index)])
              self.__graph.vs[cell_index]["in"].append(vertex)
              #print("Adding direct conection {source} -> {sink}".format(source= self.__graph.vs[vertex]["name"], sink=self.__graph.vs[cell_index]["name"]))
            else:
              if sig.is_wire(): #* sig is a primary input
                #* search for the index of the vertex named as sig.wire.name.str() in the list of vertices
                vertex = [v for v in range(len(self.__graph.vs)) if self.__graph.vs[v]["name"] == sig.wire.name.str()][0]
                #* and adds the connecting edge
                self.__graph.add_edges([(vertex, cell_index)])
                self.__graph.vs[cell_index]["in"].append(vertex)
                #print("Adding direct conection {source} -> {sink}".format(source= self.__graph.vs[vertex]["name"], sink= self.__graph.vs[cell_index]["name"]))
              else:
                if sig.data == ys.State.S1: #* sig is the constant one
                  const_1 = self.__add_C1_vertex()
                  self.__graph.add_edges([(const_1, cell_index)])
                  self.__graph.vs[cell_index]["in"].append(const_1)
                  #print("Adding direct conection {source} -> {sink}".format(source= self.__graph.vs[const_1]["name"], sink= self.__graph.vs[cell_index]["name"]))
                elif sig.data == ys.State.S0: #* sig is the constant zero
                  const_0 = self.__add_C0_vertex()
                  self.__graph.add_edges([(const_0, cell_index)])
                  self.__graph.vs[cell_index]["in"].append(const_0)
                  #print("Adding direct conection {source} -> {sink}".format(source= self.__graph.vs[const_0]["name"], sink= self.__graph.vs[cell_index]["name"]))
        if Y.is_wire():
          try:
            vertex = self.__graph.vs.find(name = Y.as_bit().wire.name.str())
            self.__graph.add_edges([(cell_index, vertex.index)])
            vertex["in"].append(cell_index)
            # print("Adding direct conection {source} -> {sink}".format(source= self.__graph.vs[vertex]["name"], sink=self.__graph.vs[cell_index]["name"]))
          except:
            pass

  def __add_cell_vertex(self, cell):
    index = [v for v in range(len(self.__graph.vs)) if self.__graph.vs[v]["name"] == cell.name.str()]
    if len(index) == 0:
      #print("Adding cell {cell_name}. Spec (msb first): {cell_spec}".format(cell_name=cell.name.str(), cell_spec=cell.parameters[ys.IdString("\LUT")].as_string()[::-1]))
      self.__graph.add_vertex()
      self.__graph.vs[-1]["type"] = ALSGraph.VertexType.CELL
      self.__graph.vs[-1]["name"] = cell.name.str()
      self.__graph.vs[-1]["hash"] = cell.name.hash()
      self.__graph.vs[-1]["spec"] = cell.parameters[ys.IdString("\LUT")].as_string()[::-1]
      self.__graph.vs[-1]["in"] = []
      self.__graph.vs[-1]["color"] = "mediumspringgreen"
      return len( self.__graph.vs) - 1
    else: return index[0]

  def __collect_signals_driven_by_cell(self, cell, sigmap, dict_of_driven_signals):
    Y = cell.connections_[ys.IdString("\Y")]
    if cell.output(ys.IdString("\Y")):
      for sig in sigmap(Y).to_sigbit_set():
        dict_of_driven_signals[sig] = { "vertex_i" : len(self.__graph.vs) - 1, "cell" : cell }
        #print("{} is driven by {}".format(sig.wire.name.str(), cell.name.str()))

  def __add_PI_vertex(self, wire):
    index = [v for v in range(len(self.__graph.vs)) if self.__graph.vs[v]["name"] == wire.name.str()]
    if len(index) == 0:
      #print("New PI: {wire_name}".format(wire_name = wire.name.str()))
      self.__graph.add_vertex()
      self.__graph.vs[-1]["type"] = ALSGraph.VertexType.PRIMARY_INPUT
      self.__graph.vs[-1]["name"] = wire.name.str()
      self.__graph.vs[-1]["hash"] = wire.name.hash()
      self.__graph.vs[-1]["spec"] = None
      self.__graph.vs[-1]["in"] = []
      self.__graph.vs[-1]["color"] = "grey"
      return len( self.__graph.vs) - 1
    else: return index[0]

  def __add_C1_vertex(self):
    index = [v for v in range(len(self.__graph.vs)) if self.__graph.vs[v]["type"] == ALSGraph.VertexType.CONSTANT_ONE]
    if len(index) == 0:
      self.__graph.add_vertex()
      self.__graph.vs[-1]["type"] = ALSGraph.VertexType.CONSTANT_ONE
      self.__graph.vs[-1]["name"] = "Constant 1"
      self.__graph.vs[-1]["hash"] = None
      self.__graph.vs[-1]["spec"] = None
      self.__graph.vs[-1]["in"] = []
      self.__graph.vs[-1]["color"] = "red"
      return len( self.__graph.vs) - 1
    else: return index[0]

  def __add_C0_vertex(self):
    index = [v for v in range(len(self.__graph.vs)) if self.__graph.vs[v]["type"] == ALSGraph.VertexType.CONSTANT_ZERO]
    if len(index) == 0:
      self.__graph.add_vertex()
      self.__graph.vs[-1]["type"] = ALSGraph.VertexType.CONSTANT_ZERO
      self.__graph.vs[-1]["name"] = "Constant 0"
      self.__graph.vs[-1]["hash"] = None
      self.__graph.vs[-1]["spec"] = None
      self.__graph.vs[-1]["in"] = []
      self.__graph.vs[-1]["color"] = "red"
      return len( self.__graph.vs) - 1
    else: return index[0]

  def __add_PO_vertex(self, wire):
    index = [v for v in range(len(self.__graph.vs)) if self.__graph.vs[v]["name"] == wire.name.str()]
    if len(index) == 0:
      #print("New PO: {wire_name}".format(wire_name = wire.name.str()))
      self.__graph.add_vertex()
      self.__graph.vs[-1]["type"] = ALSGraph.VertexType.PRIMARY_OUTPUT
      self.__graph.vs[-1]["name"] = wire.name.str()
      self.__graph.vs[-1]["hash"] = wire.name.hash()
      self.__graph.vs[-1]["spec"] = None
      self.__graph.vs[-1]["in"] = []
      self.__graph.vs[-1]["color"] = "whitesmoke"
      return len( self.__graph.vs) - 1
    else: return index[0]