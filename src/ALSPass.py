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
import sys, argparse
from pyosys import libyosys as ys
from .ALSWorker import *


class ALSPass(ys.Pass):
  def __init__(self):
    super().__init__("als", "Approximate Logic Synthesis")
    self.__args = None
    self.__top_module = None

  def py_help(self):
    ys.log("\n")
    ys.log("ALS - Approximate logic synthesis plugin, using Catalog-based AIG rewriting\n")
    ys.log("    --outdir <value>           path of the output directory, default is output/\n")
    ys.log("    --threads <amount>         select the amount of parallel worker threads, default: 1\n")
    ys.log("    --lut <inputs>             select the LUT technology to be adopted (4-LUT, 6-LUT...), default: 6\n")
    ys.log("    --catalog <filename>       path of the catalog cache\n")
    ys.log("    --timeout <value>          set the maximum timeout for the SMT synthesis of approximate LUTs\n")
    ys.log("    --nvectors <value>         set the number of test vectors for the evaluator\n")
    ys.log("    --metric <metric>          select the metric (ers | epsmax, default: ers).\n")
    ys.log("    --weight <signal> <value>  set the weight for the output signal to the specified power of two.\n")
    ys.log("    --popsize <value>          set the NSGA-II population size\n")
    ys.log("    --iter <value>             set the NSGA-II termination criterion, in terms of iterations\n")
    ys.log("    --pcross <value>           set the NSGA-II crossover probability\n")
    ys.log("    --etac <value>             set the NSGA-II crossover distribution index\n")
    ys.log("    --pmut <value>             set the NSGA-II mutation probability\n")
    ys.log("    --etam <value>             set the NSGA-II mutation distribution index\n")
#    ys.log("    --run                     : run Catalog-based AIG rewriting of top module\n")
#    ys.log("    --debug                   : enable debug output\n")
    ys.log("\n")

  def py_execute(self, args, design):
    ys.log_header(design, "Executing ALS pass (approximate logic synthesis).\n")
    ys.log_push()
    self.__cli_parser(args)
    if design.full_selection():
      self.__top_module = design.top_module()
      if self.__top_module is None:
        ys.log_cmd_error("Design has no top module, use the 'hierarchy' command to specify one.\n")
    elif len(design.selected_whole_modules_warn()) != 1:
      ys.log_cmd_error("Only one top module must be selected.\n")
      self.__top_module = design.selected_whole_modules_warn()[0]
    worker = ALSWorker(self.__top_module, self.__args.lut, self.__args.catalog, self.__args.timeout, self.__args.nvectors, self.__args.metric, self.__args.weight, self.__args.popsize, self.__args.iter, self.__args.pcross, self.__args.etac, self.__args.pmut, self.__args.etam)
    worker.run()
    ys.log_pop()

  def py_clear_flags(self):
      ys.log("Clear Flags - ALS\n")

  def __cli_parser(self, args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type = str, help = "the amount of parallel worker threads", default = "1")
    parser.add_argument("--lut", type = str, help = "Select the LUT technology to be adopted (4-LUT, 6-LUT...)", default = "4")
    parser.add_argument("--catalog", type = str, help = "Path to the catalog.", default = "lut_catalog.db")
    parser.add_argument("--outdir", type = str, help = "Path of the output directory.", default = "output/")
    parser.add_argument("--timeout", type = int, help = "Set the time budget for the SMT synthesis of LUTs, in ms.", default = 60000)
    parser.add_argument("--nvectors", type = int, help = "Set the number of test vectors for the evaluator.", default = 10000)
    parser.add_argument("--metric", type = str, help = "Select the error metric (ers | epsmax, default: ers)", default = "ers")
    parser.add_argument("--weight", action = "append", nargs = 2, help = "Set the weight for the output signal.")
    parser.add_argument("--popsize", type = int, help="NSGA-II population size.", default = 500)
    parser.add_argument("--iter", type = int, help="NSGA-II termination criterion, in terms of iterations.", default = 11)
    parser.add_argument("--pcross", type = float, help="NSGA-II crossover probability.", default = .9)
    parser.add_argument("--etac", type = float, help="NSGA-II crossover distribution index.", default = 50)
    parser.add_argument("--pmut", type = float, help="NSGA-II mutation probability.", default = .9)
    parser.add_argument("--etam", type = float, help="NSGA-II mutation distribution index.", default = 50)

#    parser.add_argument("--run", action = "store_true", help = "Set the path for the LUT-catalog to be used")
#    parser.add_argument("--debug", action = "store_true", help = "Enable debug output")
    self.__args, args = parser.parse_known_args(args)
    ys.log("Executing als-pass with the following parameters:\n")
    ys.log("\tOutput directory:   {}\n".format(str(self.__args.outdir)))
    ys.log("\tThreads:            {}\n".format(str(self.__args.threads)))
    ys.log("\tLUTs:               {}\n".format(str(self.__args.lut)))
    ys.log("\tcatalog:            {}\n".format(str(self.__args.catalog)))
    ys.log("\ttimeout:            {}\n".format(str(self.__args.timeout)))
    ys.log("\tnvectors:           {}\n".format(str(self.__args.nvectors)))
    ys.log("\tmetric:             {}\n".format(str(self.__args.metric)))
    ys.log("\tweights:            {}\n".format(str(self.__args.weight)))
    ys.log("\tNSGA-II pop.size:   {}\n".format(str(self.__args.popsize)))
    ys.log("\tNSGA-II iterations: {}\n".format(str(self.__args.iter)))
    ys.log("\tNSGA-II Pcross:     {}\n".format(str(self.__args.pcross)))
    ys.log("\tNSGA-II Ncross:     {}\n".format(str(self.__args.etac)))
    ys.log("\tNSGA-II Pmut:       {}\n".format(str(self.__args.pmut)))
    ys.log("\tNSGA-II Nmut:       {}\n".format(str(self.__args.etam)))
    
