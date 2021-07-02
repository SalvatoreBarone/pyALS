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
    ys.log("    als [options] [selection]\n")
    ys.log("    --threads <amount>        : select the amount of parallel worker threads, default: 1).\n")
    ys.log("    --catalog <filename>      : path of the catalog\n")
    ys.log("    --lut <inputs>            : select the LUT technology to be adopted (4-LUT, 6-LUT..., default: 6).\n")
    ys.log("    --metric <metric>         : select the metric (ers | epsmax, default: ers).\n")
    ys.log("    --weight <signal> <value> : set the weight for the output signal to the specified power of two.\n")
    ys.log("    --iterations <value>      : set the number of iterations for the optimizer.\n")
    ys.log("    --attempts <value>        : set the maximum attempts for the SMT synthesis of approximate LUTs.\n")
    ys.log("    --nvectors <value>        : set the number of test vectors for the evaluator.\n")
    ys.log("    --run                     : run Catalog-based AIG rewriting of top module\n")
    ys.log("    --debug                   : enable debug output\n")
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
    worker = ALSWorker(self.__top_module, self.__args.run, self.__args.lut, self.__args.catalog, self.__args.metric, self.__args.weight, self.__args.attempts, self.__args.iterations, self.__args.nvectors, self.__args.debug)
    worker.run()
    ys.log_pop()

  def py_clear_flags(self):
      ys.log("Clear Flags - ALS\n")

  def __cli_parser(self, args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type = str, help = "the amount of parallel worker threads", default = "1")
    parser.add_argument("--lut", type = str, help = "Select the LUT technology to be adopted (4-LUT, 6-LUT...)", default = "4")
    parser.add_argument("--metric", type = str, help = "Select the error metric (ers | epsmax, default: ers)", default = "ers")
    parser.add_argument("--weight", action = "append", nargs = 2, help = "Set the weight for the output signal.")
    parser.add_argument("--iterations", type = int, help = "Set the number of iterations for the optimizer.", default = 2500)
    parser.add_argument("--attempts", type = int, help = "Set the maximum attempts for the SMT synthesis of approximate LUTs.", default = 7)
    parser.add_argument("--nvectors", type = int, help = "Set the number of test vectors for the evaluator.", default = 10000)
    parser.add_argument("--catalog", type = str, help = "Run Catalog-based AIG rewriting of top module", default = "lut_catalog.db")
    parser.add_argument("--run", action = "store_true", help = "Set the path for the LUT-catalog to be used")
    parser.add_argument("--debug", action = "store_true", help = "Enable debug output")
    self.__args, args = parser.parse_known_args(args)
    ys.log("Executing als-pass with the following parameters:\n")
    ys.log("\tThreads:    " + str(self.__args.threads) + "\n")
    ys.log("\tLUTs:       " + str(self.__args.lut) + "\n")
    ys.log("\tcatalog:    " + str(self.__args.catalog) + "\n")
    ys.log("\tmetric:     " + str(self.__args.metric) + "\n")
    ys.log("\tattempts:   " + str(self.__args.attempts) + "\n")
    ys.log("\tnvectors:   " + str(self.__args.nvectors) + "\n")
    ys.log("\titerations: " + str(self.__args.iterations) + "\n")
    ys.log("\tweights:    " + str(self.__args.weight) + "\n")
