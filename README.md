# pyALS
Python implementation of the "Catalog-based Aig-rewriting Approximate Logic Synthesis" technique.

The technique is described in full details in 
> [M. Barbareschi, S. Barone, N. Mazzocca and A. Moriconi, "A Catalog-based AIG-Rewriting Approach to the Design of Approximate Components" in IEEE Transactions on Emerging Topics in Computing, vol. , no. , pp. , 2022. DOI: 10.1109/TETC.2022.3170502](https://doi.ieeecomputersociety.org/10.1109/TETC.2022.3170502)

Please, cite us!
```
@article{barbareschi2022catalog,
  title={A Catalog-based AIG-Rewriting Approach to the Design of Approximate Components},
  author={Barbareschi, Mario and Barone, Salvatore and Mazzocca, Nicola and Moriconi, Alberto},
  journal={IEEE Transactions on Emerging Topics in Computing},
  year={2022},
  publisher={IEEE}
}
```

# Using the ready-to-use docker container
pyALS has quite a lot of dependencies. You need to install Yosys (and its dependencies), GHDL (and, again, its dependencies), and so forth.
Before you get a headache, ***you can use the Docker image I have made available to you [here](https://hub.docker.com/r/salvatorebarone/pyals-docker-image).***  

Please, use the following script to run the container, that allows specifying which catalog and which folder to share with the container.
```bash
#!/bin/bash

usage() {
  echo "Usage: $0 -c catalog -s path_to_shared_folder";
  exit 1;
}

while getopts "c:s:" o; do
    case "${o}" in
        c)
            catalog=${OPTARG}
            ;;
        s)
            shared=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z "${catalog}" ] || [ -z "${shared}" ] ; then
    usage
fi

catalog=`realpath ${catalog}`
shared=`realpath ${shared}`
[ ! -d $shared ] && mkdir -p $shared
xhost local:docker
docker run --rm -e DISPLAY=unix$DISPLAY -v /tmp/.X11-unix/:/tmp/.X11-unix -v ${catalog}:/root/lut_catalog.db -v ${shared}:/root/shared -w /root --privileged -it salvatorebarone/pyals-docker-image /bin/zsh
```

If, on the other hand, you really feel the need to install everything by hand, follow the guide below step by step. 
I'm sure it will be very helpful.

# Running pyALS
You can run
```
pyALS --help
```
to obtain the list of currently supported commands (I always forgot to update this readme file...), and
```
pyALS command --help
```
to obtain the list of options available for the command ```command```.

## Main commands

pyALS supports the following main commands, each with its own set of options:
  - ```elab```: only draws the k-LUT map of the given circuit;
  - ```es```: performs the catalog-based AIG-rewriting workflow until catalog generation, i.e., including cut enumeration, and exact synthesis of approximate cuts, but it performs neither the design space exploration phase not the rewriting;
  - ```als```: performs the full catalog-based AIG-rewriting workflow, including cut enumeration, exact synthesis of approximate cuts, design space exploration and rewriting;
  - ```hdl```: performs only the rewriting step, of the catalog-based AIG-rewriting workflow, starting from the results of a previous run of the "als" command;
  - ```sw```: generates software models (in python, C and C++) for software simulations. 
  - ```metrics```: computes the all the builtin metrics (both error and hardware) for points coming from a given Pareto front.
Please kindly note you will need the file where synthesized Boolean functions are stored, i.e., the catalog-cache file. 
You can mine, which is ready-to-use, frequently updated and freely available at ```git@github.com:SalvatoreBarone/pyALS-lut-catalog```.
If you do not want to use the one I mentioned, pyALS will perform exact synthesis when needed.

Furthermore, the ```als``` and ```es``` commands requires a lot of configuration parameters, which are provided through a JSON configuration file. I will discuss its generic structure later. Now, focus on the command-line interface.

The above mentioned commands supports a lot of options, and can be concatenated, meaning that you can issue
```
pyALS [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...
```
The main options are:
```
  -c, --conf FILE      Json configuration file. For the above commands is mandatory.
  -j, --ncpus INTEGER  Number of parallel jobs to be used turing DSE. By default, it is all the available cpus
  -d, --dataset FILE   Reference dataset, in Json format.
  --help               Show this message and exit.
```
For instance, you can issue
```
./pyALS -c example/mult_2_bit/config_awce.json als hdl sw metrics
```
or
```
./pyALS -c example/mult_2_bit/config_awce.json als sw -o prova metrics -o metrics.csv
```
or
```
./pyALS -c example/mult_2_bit/config_awce.json als metrics
```
or
```
./pyALS -c example/mult_2_bit/config_awce.json metrics -o metrics.csv
```

For the complete list of options supported by a given command, please issue
```
pyALS COMMAND --help
```

The tool also provides the following sanity-related commands for catalog management:
  - ```clean```: performs a sanity check of the catalog;
  - ```expand```: attempts the catalog expansion;
  - ```stats```: computes some statistics on a catalog;
  - ```query```: check if a specification is in the catalog.
  - 

## The configuration file
The configuration file defines parameters governing the behavior of pyALS. Is is a JSON file which generic structure is reported below.
Please note that, depending on the specific command you selected, some parameters are not required, hence they can be omitted.
Furthermore, an example configuration file is provided in the ```example``` directory.

In the following, each field of the JSON file is described using C-Style comments. Note JSON does not provide any support for comments, hence you must remove them in case you copy-and-paste from the following box.

```json5
{
      "circuit" : {
        "sources" : "path_to_hdl_source",             // the HDL source file; VHDL, Verilog and System Verilog are supported. You can also pass more than one source file, using a list, i.e., ["source1", "source2"];
        "top_module" : "mult_2_bit",                  // name of the top-level entity
        // Semantic weights for input and output; you can also define weights as floating point, or even negative numbers; this is required if you want to use some of the error metrics and if you want to generate python models for simulations. Note you can omit this if you're going to use the error probability as error metric.
        "io_weights" : {
            "\\a[0]" : 1,
            "\\a[1]" : 2,
            "\\b[0]" : 1,
            "\\b[1]" : 2,
            "\\o[0]" : 1,
            "\\o[1]" : 2,
            "\\o[2]" : 4,
            "\\o[3]" : 8
        }
    },
    "output_path" : "mult_2_bit_awce",                 // path to the output directory
    "als" : {
        "cache"    : "lut_catalog.db",                 // path to the catalog-cache
        "cut_size" : 4,                                // specifies the "k" for AIG-cuts, or, alternatively, the k-LUTs for LUT-mapping during cut-enumeration, always required
        "solver"   : "btor",                           // SAT-solver to be used. It can be either btor (Boolector) or z3 (Z3-solver), always required
        "timeout"  : 60000                             // Timeout (in ms) for the exact synthesis process, always required. It is better you don't change its default value.              
    },
    "error" : {                                        // This section defines error-related stuff
        "metrics"      : ["mse"],                      // Error metric(s) to be used during Design-Space exploration. Please note you can specify more than one metric. See supported metrics for more.
        "threshold"    : [1e+3],                       // The error threshold. Please note you can specify more than one threshold, one for each of the error metrics.
        "vectors"      : 1000,                         // The amount of test vectors to evaluate the error. "0" here will result in exhaustive test pattern evaluation.
        "dataset"      : "path_to_the_dataset"         // Alternatively, you can specify a custom set of test vectors as either JSON, CSV or xsls file. ***THIS WILL OVERRIDE THE vectors FIELD! ***. See the following sections for more
    },
    "hardware" : {                                     // Hardware related stuff
        "metric" : ["gates", "depth", "switching"]     // hardware metric(s) to be optimized (AIG-gates, AIG-depth, or LUT switching activity). Please note you can specify more than one metric.
    },
    "amosa" : {                                        // Parameters governing the Archived Multi-Objective Simulated-Annealing optimization heuristic 
        "archive_hard_limit"       : 100,              // Archive hard limit for the AMOSA optimization heuristic, see [1]
        "archive_soft_limit"       : 200,              // Archive soft limit for the AMOSA optimization heuristic, see [1]
        "archive_gamma"            : 2,                // Gamma parameter for the AMOSA optimization heuristic, see [1]
        
        "clustering_iterations"    : 300,              // maximum iterations performed by the clustering algorithm

        "initial_temperature"      : 500,              // Initial temperature of the matter for the AMOSA optimization heuristic, see [1]
        "cooling_factor"           : 0.95,             // It governs how quickly the temperature of the matter decreases during the annealing process, see [1]
        "hill_climbing_iterations" : 500,              // the number of iterations performed during the initial hill-climbing refinement, see [1];
        "annealing_iterations"     : 750,              // The amount of refinement iterations performed during the main-loop of the AMOSA heuristic, see [1]
        
        "annealing_strength"       : 1,                // Governs the strength of random perturbations during the annealing phase; specifically, the number of variables whose value is affected by perturbation.

        // Termination criterion. Termination criterion can be combined!
        "final_temperature"        : 1e-7,             // This is the classic termination criterion for simulated annealing: when the temperature of the matter is lower than the threshold, the algorithm is terminated. See [1] for details.
        "max_duration"             : "3:30",           // the termination can also be based on the time of the algorithm to be executed. Note the initial hill-climbing is taken into account!***). For instance, to run an algorithm for 3 hours, 30 minutes, the termination can be defined as "3:30".
        "early_termination"        : 20,               // the most interesting stopping criterion is to use objective space change to decide whether to terminate the algorithm. Here, we resort to a simple and efficient procedure to determine whether to stop or not, described in [2]: it is based on the inter-generational distance (IGD), and it allows to stop the algorithm in case it cannot improve the Pareto front in a sequence of iterations. Say you want to stop if the algorithm is unable to improve in 10 iterations (meaning complete algorithm iterations, each of which consists of the number of annealing iterations as defined by the corresponding configuration parameter); then, the termination criterion can be defined as 10
    }
}
```

## Using a custom dataset
A custom set of input vectors can be used for error estimation. It can be either in the CSV or XLSX format. The first row of the file MUST specify the name of primary inputs, and for CSV files, the separator must be the semicolon ";". An example follows

```
\a[0];\a[1];\b[0];\b[1]
0;0;0;0
0;0;0;1
0;0;1;0
0;0;1;1
0;1;0;0
0;1;0;1
0;1;1;0
0;1;1;1
1;0;0;0
```
Please, note the backslash "\" leading the name of primary inputs.


## Error metrics

pyALS actually provides the user to define the error metric to be used during optimization. It can be selected through the ```metric``` field of the ```error``` section of the configuration file.
The latter can be set to
- "ep" for error-probability <!-- e_{\text{prob}}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} [\![  f(x) \ne \hat{f}(x) ]\!]  -->, <img src="https://latex.codecogs.com/svg.image?e_{\text{prob}}(f,\hat{f})&space;=&space;\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;[\![&space;&space;f(x)&space;\ne&space;\hat{f}(x)&space;]\!]&space;" title="https://latex.codecogs.com/svg.image?e_{\text{prob}}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} [\![ f(x) \ne \hat{f}(x) ]\!] " />
- "awce" for absolute worst-case error <!-- e_{\text{awce}}(f,\hat{f}) = \max_{x \in \mathbb{B}^n} |  f(x) - \hat{f}(x) | --><img src="https://latex.codecogs.com/svg.image?e_{\text{awce}}(f,\hat{f})&space;=&space;\max_{x&space;\in&space;\mathbb{B}^n}&space;|&space;&space;f(x)&space;-&space;\hat{f}(x)&space;|" title="https://latex.codecogs.com/svg.image?e_{\text{awce}}(f,\hat{f}) = \max_{x \in \mathbb{B}^n} | f(x) - \hat{f}(x) |" />
- "mae" for mean absolute error <!-- e_{\text{mae}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} |  f(x) - \hat{f}(x) | -->, <img src="https://latex.codecogs.com/svg.image?e_{\text{mae}}(f,\hat{f})&space;=&space;\frac{1}{2^n}\sum_{x&space;\in&space;\mathbb{B}^n}&space;|&space;&space;f(x)&space;-&space;\hat{f}(x)&space;|" title="https://latex.codecogs.com/svg.image?e_{\text{mae}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} | f(x) - \hat{f}(x) |" />
- "wre" for worst-case relative error <!-- e_{\text{wre}}(f,\hat{f}) = \max_{x \in \mathbb{B}^n} \left|  1 - \frac{\hat{f}(x)}{f(x)}  \right| --> <img src="https://latex.codecogs.com/svg.image?e_{\text{wre}}(f,\hat{f})&space;=&space;\max_{x&space;\in&space;\mathbb{B}^n}&space;\left|&space;&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;&space;\right|" title="https://latex.codecogs.com/svg.image?e_{\text{wre}}(f,\hat{f}) = \max_{x \in \mathbb{B}^n} \left| 1 - \frac{\hat{f}(x)}{f(x)} \right|" />
- "mre" for mean relative error <!-- e_{\text{wre}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} \frac{| \hat{f}(x) - f(x) |}{1 + |f(x)|} --> <img src="https://latex.codecogs.com/svg.image?e_{\text{wre}}(f,\hat{f})&space;=&space;\frac{1}{2^n}\sum_{x&space;\in&space;\mathbb{B}^n}&space;\frac{|&space;\hat{f}(x)&space;-&space;f(x)&space;|}{1&space;&plus;&space;|f(x)|}" title="https://latex.codecogs.com/svg.image?e_{\text{wre}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} \frac{| \hat{f}(x) - f(x) |}{1 + |f(x)|}" />
- "mare" for mean absolute relative error <!-- e_{\text{mare}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} \left|\frac{ \hat{f}(x) - f(x) }{f(x)} \right| --> <img src="https://latex.codecogs.com/svg.image?&space;e_{\text{mare}}(f,\hat{f})=\frac{1}{2^n}\sum_{x\in\mathbb{B}^n}\left|\frac{\hat{f}(x)-f(x)}{f(x)}\right|" title=" e_{\text{mare}}(f,\hat{f})=\frac{1}{2^n}\sum_{x\in\mathbb{B}^n}\left|\frac{\hat{f}(x)-f(x)}{f(x)}\right|" />

- "mse" for mean squared error <!-- e_{\text{mse}}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left(  \hat{f}(x) - f(x)  \right)^2 --> <img src="https://latex.codecogs.com/svg.image?e_{\text{mse}}(f,\hat{f})&space;=&space;\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left(&space;&space;\hat{f}(x)&space;-&space;f(x)&space;&space;\right)^2" title="https://latex.codecogs.com/svg.image?e_{\text{mse}}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left( \hat{f}(x) - f(x) \right)^2" />
- "me" for mean error <!-- e_{\text{me}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( f(x) - \hat{f}(x) \right) \cdot \left(f(x) - \hat{f}(x)\right) --> <img src="https://latex.codecogs.com/svg.image?&space;e_{\text{me}}(f,\hat{f})&space;=&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;P&space;\left(&space;f(x)&space;-&space;\hat{f}(x)&space;\right)&space;\cdot&space;\left(f(x)&space;-&space;\hat{f}(x)\right)" title="https://latex.codecogs.com/svg.image? e_{\text{me}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( f(x) - \hat{f}(x) \right) \cdot \left(f(x) - \hat{f}(x)\right)" />, where <img src="https://latex.codecogs.com/svg.image?&space;P&space;\left(&space;f(x)&space;-&space;\hat{f}(x)&space;\right)" title="https://latex.codecogs.com/svg.image? P \left( f(x) - \hat{f}(x) \right)" /> is the probability of <img src="https://latex.codecogs.com/svg.image?\left(&space;f(x)&space;-&space;\hat{f}(x)&space;\right)" title="https://latex.codecogs.com/svg.image?\left( f(x) - \hat{f}(x) \right)" /> to occur;
- "med" for mean error distance <!-- e_{\text{med}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( \left|f(x) - \hat{f}(x)\right| \right) \cdot \left|f(x) - \hat{f}(x)\right| --> <img src="https://latex.codecogs.com/svg.image?e_{\text{med}}(f,\hat{f})&space;=&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;P&space;\left(&space;\left|f(x)&space;-&space;\hat{f}(x)\right|&space;\right)&space;\cdot&space;\left|f(x)&space;-&space;\hat{f}(x)\right|" title="https://latex.codecogs.com/svg.image?e_{\text{med}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( \left|f(x) - \hat{f}(x)\right| \right) \cdot \left|f(x) - \hat{f}(x)\right|" />, where <img src="https://latex.codecogs.com/svg.image?P&space;\left(&space;\left|f(x)&space;-&space;\hat{f}(x)\right|&space;\right)" title="https://latex.codecogs.com/svg.image?P \left( \left|f(x) - \hat{f}(x)\right| \right)" /> is the probability of <img src="https://latex.codecogs.com/svg.image?\left|f(x)&space;-&space;\hat{f}(x)\right|" title="https://latex.codecogs.com/svg.image?\left|f(x) - \hat{f}(x)\right|" /> to occur;
- "mred" for mean relative error distance <!-- e_{\text{mred}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( \left| 1 - \frac{\hat{f}(x)}{f(x)} \right| \right) \cdot \left| 1 - \frac{\hat{f}(x)}{f(x)} \right| --><img src="https://latex.codecogs.com/svg.image?e_{\text{mred}}(f,\hat{f})&space;=&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;P&space;\left(&space;\left|&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;\right|&space;\right)&space;\cdot&space;\left|&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;\right|" title="https://latex.codecogs.com/svg.image?e_{\text{mred}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( \left| 1 - \frac{\hat{f}(x)}{f(x)} \right| \right) \cdot \left| 1 - \frac{\hat{f}(x)}{f(x)} \right|" />, where <img src="https://latex.codecogs.com/svg.image?P&space;\left(&space;\left|&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;\right|&space;\right)" title="https://latex.codecogs.com/svg.image?P \left( \left| 1 - \frac{\hat{f}(x)}{f(x)} \right| \right)" /> is the probability of error <img src="https://latex.codecogs.com/svg.image?\left|&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;\right|" title="https://latex.codecogs.com/svg.image?\left| 1 - \frac{\hat{f}(x)}{f(x)} \right|" /> to occur;
- "rmsed" for the root mean squared error <!-- e_{\text{rmse}}(f,\hat{f}) = \sqrt{\frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left(  \hat{f}(x) - f(x)  \right)^2} --> <img src="https://latex.codecogs.com/svg.image?e_{\text{rmse}}(f,\hat{f})&space;=&space;\sqrt{\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left(&space;&space;\hat{f}(x)&space;-&space;f(x)&space;&space;\right)^2}" title="https://latex.codecogs.com/svg.image?e_{\text{rmse}}(f,\hat{f}) = \sqrt{\frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left( \hat{f}(x) - f(x) \right)^2}" />
- "vared" for the variance of the error distance <!-- e_{\sigma}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left[  \left(f(x) - \hat{f}(x)\right) - \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left(f(x) - \hat{f}(x)\right) \right]^2 --><img src="https://latex.codecogs.com/svg.image?e_{\sigma}(f,\hat{f})&space;=&space;\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left[&space;&space;\left(f(x)&space;-&space;\hat{f}(x)\right)&space;-&space;\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left(f(x)&space;-&space;\hat{f}(x)\right)&space;\right]^2" title="https://latex.codecogs.com/svg.image?e_{\sigma}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left[ \left(f(x) - \hat{f}(x)\right) - \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left(f(x) - \hat{f}(x)\right) \right]^2" />
 
## Coping with large circuits
Large circuits may imply a huge number of decision variables being involved in the design process. 
For this reason, pyALS allows the circuit design problem to be faced using optimization heuristics suitable for large scale optimization problems, i.e., problems involving more the 100 decision variables.

Currently, two heuristics are supported, both based on the divide-and-conquer strategy:
  - the dynamic random grouping [3], that randomly divides the decision variables into several groups;
  - the differential value analysis [4]: it groups decision variables based on their interaction and separability;
    using this strategys requires specifying *transfer strategies* [5], that are divided into two consecutive steps. The first step combines interaction information of different objective functions, and two Transfer Strategies for Objective functions(TSO) have been defined, namely 
      - *TSO_any*, regards two variables xi and xj as interacting, if an interaction exists in *any* of the objective functions 
      - *TSO_all*, regards two variables xi and xj as interacting, if an interaction exists in *all* of the objective functions
    and two Transfer Strategies for Variables (TSV), namely
      - *TSV_any*, a variable xi is added to a group if the combined interaction graph contains an edge between xi and any variable xj in the group. 
      - *TSV_all*, a variable xi is added to a group if the combined interaction graph contains an edge between xi and all the other variable xj in the group.

You can specify which strategy to be used in the configuration file, as it follows:
```json5

"amosa": {
  ...
        "grouping"                 : "DRG", //use random grouping ("DRG", "drg", "random" are supported)
  ...
  }
```
```json5
"amosa": {
  ...
        "grouping"                 : "DVG", //use differential value analysis ("dvg", "DVG", "dvg2", "DVG2", "differential" are supported)
        "tso"                      : "any", // tso "any" or "all"
        "tsv"                      : "any", // tsv "any" or "all"
  ...
  }
```

## Understanding the log prints
When performing the ```als`` command, during the annealing procedure, the optimizers will print several statistical information in a table format.
These are pretty useful for evaluating the effectiveness of the optimization process -- in specific whether it's going toward either convergence or diversity in the population, etc. -- so it's worth discoursing them.

  - *temp*.: it is the current temperature of the matter; refer to [1] for further details on its impact on the optimization process;
  - *eval*: it is the number of fitness-function evaluations;
  - *nds*: it is the number of non-dominated solutions the algorithm found until then;
  - *feas*: it is the number of **feasible** non-dominated solutions (i.e., those satisfying constraints) the algorithm found until then;
  - *cv min* and *cv avg*: minimum and average constraint violation, computed on unfeasible non-dominated solutions the algorithm found until then;
  - *D\** and *Dnad*: movement of the *ideal* and *nadir* idealized extreme points in the object-space; whether the algotithm is going toward convergence, they tend to be higher (the Pareto front is moving a lot!); see [2] for further details;
  - *phi*: the *intergenerational distance index*, computed on candidate solutions from the previous annealing iteration *P'* and candidate solutions resulting from the very last annealing iteration *P*; this allows monitoring; if the Pareto front is stationary, and can be improved neither by convergence nor by diversity, this value is close to zero; this metric is taken into consideration to determine the early termination condition; see [3] for further details;
  - *C(P', P)* and *C(P, P')*: the *coverage index* as defined in [6], computed on candidate solutions from the previous annealing iteration *P'* and candidate solutions resulting from the very last annealing iteration *P* and vice-versa, respectively; in general, *C(A,B)* is percentage the solutions in *B* that are dominated by at least one solution in *A*, where *A* and *B* are two Pareto fronts; therefore, *C(P, P')* should be alway greater than *C(P', P)* through the optimization process.


# Manual installation

Come on... Do you really want to install everything by hand!? [You can use a ready to use Docker container!](#using-the-ready-to-use-docker-container)

No? Ok, then... Note that this guide has been tested on Debian 11.

### Preliminaries
You need to install some basic dependencies. So, run
```bash
# apt-get install --fix-missing -y git bison clang cmake curl flex fzf g++ gnat gawk libffi-dev libreadline-dev libsqlite3-dev  libssl-dev make p7zip-full pkg-config python3 python3-dev python3-pip tcl-dev vim-nox wget xdot zlib1g-dev zlib1g-dev zsh libboost-dev libboost-filesystem-dev libboost-graph-dev libboost-iostreams-dev libboost-program-options-dev libboost-python-dev libboost-serialization-dev libboost-system-dev libboost-thread-dev
```

You also need to create some symbolic links.
```bash
# ln -s /usr/lib/x86_64-linux-gnu/libtinfo.so /usr/lib/x86_64-linux-gnu/libtinfo.so.5
# ln -fs /usr/lib/x86_64-linux-gnu/libboost_python39.a /usr/lib/x86_64-linux-gnu/libboost_python.a
# ln -fs /usr/lib/x86_64-linux-gnu/libboost_python39.so /usr/lib/x86_64-linux-gnu/libboost_python.so
```
Please, kindly note you are required to amend any differences concerning the python version. I'm using python 3.9 here.

### Cloning the repo
pyALS uses git submodules, so you have to clone this repository as follows
```bash
git clone git@github.com:SalvatoreBarone/pyALS.git
git submodule init
git submodule update
```
or
```bash
git clone --recursive git@github.com:SalvatoreBarone/pyALS.git
```

### Installing Yosys
First, you need to clone Yosys from its public repository
```bash
$ git clone https://github.com/YosysHQ/yosys
```
This will create a ```yosys``` sub-directory inside your current directory. Now move into the ```yosys``` directory, and create a ```Makefile.conf``` file.
```bash
$ cd yosys
$ touch Makefile.conf
```
Paste the following into the ```Makefile.conf``` file.
```
CONFIG := clang
CXXFLAGS += -I/usr/include/python3.9/ -fPIC
ENABLE_LIBYOSYS=1
ENABLE_PYOSYS=1
PYTHON_EXECUTABLE=/usr/bin/python3 
PYTHON_VERSION=3.9 
PYTHON_CONFIG=python3-config 
PYTHON_DESTDIR=/usr/local/lib/python3.9/dist-packages
BOOST_PYTHON_LIB=/usr/lib/x86_64-linux-gnu/libboost_python.so -lpython3.9
```
Please, kindly note you are required to amend any differences concerning the python version. I'm using python 3.9 here.
Now you need to a little quick fix to yosys: edit the ```kernel/yosys.cc``` file, searching for the definition of the 
```run_pass``` function. Comment the call to the ```log``` function as follows.
```cpp
void run_pass(std::string command, RTLIL::Design *design)
{
	if (design == nullptr)
		design = yosys_design;

	//log("\n-- Running command `%s' --\n", command.c_str());

	Pass::call(design, command);
}
```
This will remove redundant logs while running the optimizer.
Ok, now you are ready.
```bash
$ make -j `nproc`
# make install
# ln -s `realpath yosys` /usr/bin
# ln -s `realpath yosys-abc` /usr/bin
```

### Installing GHDL
GHDL and its Yosys plugin are required to process VHDL-encoded designs. 
Please, kindly note that you will be able to successfully install the GHDL Yosys plugin only if you successfully installed Yosys. 
Let's install GHDL first. As always, you need to clone GHDL from ist public repository and compile it.
```bash
$ git clone https://github.com/ghdl/ghdl.git
$ cd ghdl
$ ./configure --prefix=/usr/local
$ make
# make install
```
The same applies to its Yosys plugin. 
```bash
$ git clone https://github.com/ghdl/ghdl-yosys-plugin.git
$ cd ghdl-yosys-plugin
$ make
# make install
```

### Installing python dependencies
You're almost done, the last step is to install python dependencies. Some of them can be installed automatically, some others must be installed manually.Let's start with the latter ones. 

You must install the [pyAMOSA](https://github.com/SalvatoreBarone/pyAMOSA) module
```
$ git clone https://github.com/SalvatoreBarone/pyAMOSA.git
$ cd pyAMOSA
# python3 setup.py install
$ cd ..
```
and the [pyALSlib](https://github.com/SalvatoreBarone/pyALSlib) module
```
$ git clone https://github.com/SalvatoreBarone/pyALSlib.git
$ cd pyALSlib
# python3 setup.py install
$ cd ..
```

Pertaining to other dependencies, installing them is quite simple, and you just need to issue the following command from within the pyALS directory.
```bash
pip3 install -r requirements.txt 
```




# References
1. Bandyopadhyay, S., Saha, S., Maulik, U., & Deb, K. (2008). A simulated annealing-based multiobjective optimization algorithm: AMOSA. IEEE transactions on evolutionary computation, 12(3), 269-283.
2. Blank, Julian, and Kalyanmoy Deb. "A running performance metric and termination criterion for evaluating evolutionary multi-and many-objective optimization algorithms." 2020 IEEE Congress on Evolutionary Computation (CEC). IEEE, 2020.
3. Song, An, Qiang Yang, Wei-Neng Chen, e Jun Zhang. "A random-based dynamic grouping strategy for large scale multi-objective optimization". In 2016 IEEE Congress on Evolutionary Computation (CEC), 468–75, 2016. https://doi.org/10.1109/CEC.2016.7743831.
4. Omidvar, Mohammad Nabi, Ming Yang, Yi Mei, Xiaodong Li, e Xin Yao. "DG2: A Faster and More Accurate Differential Grouping for Large-Scale Black-Box Optimization". IEEE Transactions on Evolutionary Computation 21, fasc. 6 (dicembre 2017): 929–42. https://doi.org/10.1109/TEVC.2017.2694221.
5. Sander, Frederick, Heiner Zille, e Sanaz Mostaghim. "Transfer Strategies from Single- to Multi-Objective Grouping Mechanisms". In Proceedings of the Genetic and Evolutionary Computation Conference, 729–36. Kyoto Japan: ACM, 2018. https://doi.org/10.1145/3205455.3205491.
6. Zitzler, E., e L. Thiele. "Multiobjective evolutionary algorithms: a comparative case study and the strength Pareto approach". IEEE Transactions on Evolutionary Computation 3, fasc. 4 (novembre 1999).


