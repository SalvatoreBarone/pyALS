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
  - ```es```: performs the catalog-based AIG-rewriting workflow until catalog generation, i.e., including cut enumeration, and exact synthesis of approximate cuts, but it performs neither the design space exploration phase not the rewriting;
  - ```generate```: performs only the rewriting step, of the catalog-based AIG-rewriting workflow, starting from the results of a previous run of the "als" command;
  - ```als```: performs the full catalog-based AIG-rewriting workflow, including cut enumeration, exact synthesis of approximate cuts, design space exploration and rewriting;
  - ```elaborate```: only draws the k-LUT map of the given circuit;
  - ```pymodels```: generates software models (in python) for software simulations. 

Please kindly note you will need the file where synthesized Boolean functions are stored, i.e., the catalog-cache file. 
You can mine, which is ready-to-use, frequently updated and freely available at ```git@github.com:SalvatoreBarone/pyALS-lut-catalog```.
If you do not want to use the one I mentioned, pyALS will perform exact synthesis when needed.

Furthermore, the ```als``` and ```es``` commands requires a lot of configuration parameters, which are provided through a JSON configuration file. 
I will its generic structure later. Now, focus on the command-line interface.

## Other commands

The pyALS tool also provide the following commands for input-aware approximation:
  
  - ```template```: generates a CSV file for specifying the input dataset to be used for error assessment;
  - ```randomsplit```: splits the complete input-set in N partitions, using random sampling without repetitions.

Furthermore, the tool also provides the following sanity-related commands for catalog management:
  - ```clean```: performs a sanity check of the catalog;
  - ```expand```: attempts the catalog expansion;
  - ```stats```: computes some statistics on a catalog;
  - ```query```: check if a specification is in the catalog.
  - 
## Command line interface

You can use the following commands

### The ```elaborate``` command
Draws a k-LUT map of the given circuit

Usage: 
```
pyALS elaborate [OPTIONS]
```
Options:
```
  --source TEXT  specify the input HDL source file  [required]
  --top TEXT     specify the top-module name  [required]
  --lut TEXT     specify the LUT size  [required]
  --output TEXT  Output file.  [required]
```
Example:
```
./pyALS plot --source example/mult_2_bit.sv --top mult_2_bit -lut 4 -output mult_2_bit.pdf 
```


### The ```es``` command
Performs the catalog-based AIG-rewriting workflow until catalog generation, i.e., including cut enumeration, and exact synthesis of approximate cuts, but it performs neither the design space exploration phase not the rewriting.

Usage: 
```
pyALS es CONFIGFILE
```
where:
```
  CONFIGFILE is the path of the configuration file
```
Example:
```
./pyALS es /path_to_config.json 
```


### The ```als``` command
Performs the full catalog-based AIG-rewriting workflow, including cut enumeration, exact synthesis of approximate cuts, design space exploration and rewriting.

Usage: 
```
pyALS als CONFIGFILE
```
where:
```
  CONFIGFILE is the path of the configuration file
```
Example:
```
pyALS als example/mult_2_bit/config_awce.json
```

### The ```generate``` command
Performs the rewriting step of the catalog-based AIG-rewriting workflow, starting from the results of a previous run of the "als" command

Usage: 
```
pyALS generate CONFIGFILE
```
where:
```
  CONFIGFILE is the path of the configuration file
```
Example:
```
pyALS generate example/mult_2_bit/config_awce.json
```

### The ```pymodels``` command
Generates software models of twp-inouts-one-output arithmetic circuits resulting from the 'als' command, for software simulations. You can select which models to be generated using the available options.
Usage: 
```
pyALS pymodels [OPTIONS] CONFIGFILE MODELDESCRIPTIONFILE
```
where:

  - ```CONFIGFILE``` is the path of the JSON configuration file containing all   parameters which are needed to the tool. 
  - ```OUTFILE``` it is the path to the output file containing generated models.

Options:
  - ```-f```: Enables using the floating-point representation for look-up tables

Example:
```
pyALS pymodels example/mult_2_bit/config_awce.json output.py
```

### The ```template``` command
Creates a CSV template file to be used to define a dataset while optimizing a given error metric

Usage:
```
pyALS template [OPTIONS]
```
Options:
```
  --source TEXT  specify the input HDL source file  [required]
  --top TEXT     specify the top-module name  [required]
  --output TEXT  Output file.  [required]
  --separator    specify the column separator
```
Example:
```
./pyALS plot --source example/mult_2_bit.sv --top mult_2_bit --output dataset.csv 
```

## The  ```randomsplit``` command
Splits the complete input-set in N partitions, using random sampling without repetitions.

Usage:
```
pyALS dataset [OPTIONS]
```
Options:
```
  --source TEXT  specify the input HDL source file  [required]
  --top TEXT     specify the top-module name  [required]
  --splits INT   number of partitions  [required]
  --outputdir    output directory [required]
```

## The configuration file
The configuration file defines parameters governing the behavior of pyALS. Is is a JSON file which generic structure is reported below.
Please note that, depending on the specific command you selected, some parameters are not required, hence they can be omitted.
Furthermore, an example configuration file is provided in the ```example``` directory.

In the following, each field of the JSON file is described using C-Style comments. Note JSON does not provide any support for comments, hence you must remove them in case you copy-and-paste from the following box.

```json
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
        "metrics"      : ["mse"],                      // Error metric(s) to be used during Design-Space exploration. . Please note you can specify more than one metric. See supported metrics for more.
        "threshold"    : 1e+3,                         // The error threshold
        "vectors"      : 10000,                        // The number of test vectors for error assessment. Using the value "0" will unlock exhaustive evaluation, i.e., it will cause the tool to evaluate the error for every possible input assignment.
        "dataset" : "/path_to_csv_or_json_dataset"     // Input dataset to be used for error assessment, in csv or json format. A csv template can be generated using the "template" command of the tool.
    },
    "hardware" : {                                     // Hardware related stuff
        "metric" : ["gates", "depth", "switching"]     // hardware metric(s) to be optimized (AIG-gates, AIG-depth, or LUT switching activity). Please note you can specify more than one metric.
    },
    "amosa" : {                                        // Parameters governing the Archived Multi-Objective Simulated-Annealing optimization heuristic 
        "archive_hard_limit"       : 100,              // Archive hard limit for the AMOSA optimization heuristic, see [1]
        "archive_soft_limit"       : 200,              // Archive soft limit for the AMOSA optimization heuristic, see [1]
        "archive_gamma"            : 2,                // Gamma parameter for the AMOSA optimization heuristic, see [1]
        "clustering_iterations"    : 300,              // maximum iterations performed by the clustering algorithm
        "hill_climbing_iterations" : 500,              // the number of iterations performed during the initial hill-climbing refinement, see [1];
        "initial_temperature"      : 500,              // Initial temperature of the matter for the AMOSA optimization heuristic, see [1]
        "final_temperature"        : 0.0000001,        // Final temperature of the matter for the AMOSA optimization heuristic, see [1]
        "cooling_factor"           : 0.95,             // It governs how quickly the temperature of the matter decreases during the annealing process, see [1]
        "annealing_iterations"     : 750,              // The amount of refinement iterations performed during the main-loop of the AMOSA heuristic, see [1]
        "annealing_strength"       : 1,                // Governs the strength of random perturbations during the annealing phase; specifically, the number of variables whose value is affected by perturbation.
        "early_termination"        : 20,               // Early termination window. See [2]. Set it to zero in order to disable early-termination. Default is 20.
        "multiprocess_enabled"     : true              // Enables/disables synchronous multiprocessing with intensive solution exchanges in AMOSA. While using built-in metrics, it should be disabled.
    }
}
```

## Error metrics

pyALS actually provides the user to define the error metric to be used during optimization. It can be selected through the ```metric``` field of the ```error``` section of the configuration file.
The latter can be set to
- "ep" for error-probability <!-- e_{\text{prob}}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} [\![  f(x) \ne \hat{f}(x) ]\!]  -->, <img src="https://latex.codecogs.com/svg.image?e_{\text{prob}}(f,\hat{f})&space;=&space;\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;[\![&space;&space;f(x)&space;\ne&space;\hat{f}(x)&space;]\!]&space;" title="https://latex.codecogs.com/svg.image?e_{\text{prob}}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} [\![ f(x) \ne \hat{f}(x) ]\!] " />
- "awce" for absolute worst-case error <!-- e_{\text{awce}}(f,\hat{f}) = \max_{x \in \mathbb{B}^n} |  f(x) - \hat{f}(x) | --><img src="https://latex.codecogs.com/svg.image?e_{\text{awce}}(f,\hat{f})&space;=&space;\max_{x&space;\in&space;\mathbb{B}^n}&space;|&space;&space;f(x)&space;-&space;\hat{f}(x)&space;|" title="https://latex.codecogs.com/svg.image?e_{\text{awce}}(f,\hat{f}) = \max_{x \in \mathbb{B}^n} | f(x) - \hat{f}(x) |" />
- "mae" for mean absolute error <!-- e_{\text{mae}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} |  f(x) - \hat{f}(x) | -->, <img src="https://latex.codecogs.com/svg.image?e_{\text{mae}}(f,\hat{f})&space;=&space;\frac{1}{2^n}\sum_{x&space;\in&space;\mathbb{B}^n}&space;|&space;&space;f(x)&space;-&space;\hat{f}(x)&space;|" title="https://latex.codecogs.com/svg.image?e_{\text{mae}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} | f(x) - \hat{f}(x) |" />
- "wre" for worst-case relative error <!-- e_{\text{wre}}(f,\hat{f}) = \max_{x \in \mathbb{B}^n} \left|  1 - \frac{\hat{f}(x)}{f(x)}  \right| --> <img src="https://latex.codecogs.com/svg.image?e_{\text{wre}}(f,\hat{f})&space;=&space;\max_{x&space;\in&space;\mathbb{B}^n}&space;\left|&space;&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;&space;\right|" title="https://latex.codecogs.com/svg.image?e_{\text{wre}}(f,\hat{f}) = \max_{x \in \mathbb{B}^n} \left| 1 - \frac{\hat{f}(x)}{f(x)} \right|" />
- "mre" for mean relative error <!-- e_{\text{wre}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} \left|  1 - \frac{\hat{f}(x)}{f(x)}  \right| --> <img src="https://latex.codecogs.com/svg.image?e_{\text{wre}}(f,\hat{f})&space;=&space;\frac{1}{2^n}\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left|&space;&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;&space;\right|" title="https://latex.codecogs.com/svg.image?e_{\text{wre}}(f,\hat{f}) = \frac{1}{2^n}\sum_{x \in \mathbb{B}^n} \left| 1 - \frac{\hat{f}(x)}{f(x)} \right|" />
- "mse" for mean squared error <!-- e_{\text{mse}}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left(  \hat{f}(x) - f(x)  \right)^2 --> <img src="https://latex.codecogs.com/svg.image?e_{\text{mse}}(f,\hat{f})&space;=&space;\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left(&space;&space;\hat{f}(x)&space;-&space;f(x)&space;&space;\right)^2" title="https://latex.codecogs.com/svg.image?e_{\text{mse}}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left( \hat{f}(x) - f(x) \right)^2" />
- "med" for mean error distance <!-- e_{\text{med}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( \left|f(x) - \hat{f}(x)\right| \right) \cdot \left|f(x) - \hat{f}(x)\right| --> <img src="https://latex.codecogs.com/svg.image?e_{\text{med}}(f,\hat{f})&space;=&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;P&space;\left(&space;\left|f(x)&space;-&space;\hat{f}(x)\right|&space;\right)&space;\cdot&space;\left|f(x)&space;-&space;\hat{f}(x)\right|" title="https://latex.codecogs.com/svg.image?e_{\text{med}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( \left|f(x) - \hat{f}(x)\right| \right) \cdot \left|f(x) - \hat{f}(x)\right|" />, where <img src="https://latex.codecogs.com/svg.image?P&space;\left(&space;\left|f(x)&space;-&space;\hat{f}(x)\right|&space;\right)" title="https://latex.codecogs.com/svg.image?P \left( \left|f(x) - \hat{f}(x)\right| \right)" /> is the probability of <img src="https://latex.codecogs.com/svg.image?\left|f(x)&space;-&space;\hat{f}(x)\right|" title="https://latex.codecogs.com/svg.image?\left|f(x) - \hat{f}(x)\right|" /> to occur;
- "mred" for mean relative error distance <!-- e_{\text{mred}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( \left| 1 - \frac{\hat{f}(x)}{f(x)} \right| \right) \cdot \left| 1 - \frac{\hat{f}(x)}{f(x)} \right| --><img src="https://latex.codecogs.com/svg.image?e_{\text{mred}}(f,\hat{f})&space;=&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;P&space;\left(&space;\left|&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;\right|&space;\right)&space;\cdot&space;\left|&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;\right|" title="https://latex.codecogs.com/svg.image?e_{\text{mred}}(f,\hat{f}) = \sum_{x \in \mathbb{B}^n} P \left( \left| 1 - \frac{\hat{f}(x)}{f(x)} \right| \right) \cdot \left| 1 - \frac{\hat{f}(x)}{f(x)} \right|" />, where <img src="https://latex.codecogs.com/svg.image?P&space;\left(&space;\left|&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;\right|&space;\right)" title="https://latex.codecogs.com/svg.image?P \left( \left| 1 - \frac{\hat{f}(x)}{f(x)} \right| \right)" /> is the probability of error <img src="https://latex.codecogs.com/svg.image?\left|&space;1&space;-&space;\frac{\hat{f}(x)}{f(x)}&space;\right|" title="https://latex.codecogs.com/svg.image?\left| 1 - \frac{\hat{f}(x)}{f(x)} \right|" /> to occur;
- "rmsed" for the root mean squared error <!-- e_{\text{rmse}}(f,\hat{f}) = \sqrt{\frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left(  \hat{f}(x) - f(x)  \right)^2} --> <img src="https://latex.codecogs.com/svg.image?e_{\text{rmse}}(f,\hat{f})&space;=&space;\sqrt{\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left(&space;&space;\hat{f}(x)&space;-&space;f(x)&space;&space;\right)^2}" title="https://latex.codecogs.com/svg.image?e_{\text{rmse}}(f,\hat{f}) = \sqrt{\frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left( \hat{f}(x) - f(x) \right)^2}" />
- "vared" for the variance of the error distance <!-- e_{\sigma}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left[  \left(f(x) - \hat{f}(x)\right) - \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left(f(x) - \hat{f}(x)\right) \right]^2 --><img src="https://latex.codecogs.com/svg.image?e_{\sigma}(f,\hat{f})&space;=&space;\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left[&space;&space;\left(f(x)&space;-&space;\hat{f}(x)\right)&space;-&space;\frac{1}{2^n}&space;\sum_{x&space;\in&space;\mathbb{B}^n}&space;\left(f(x)&space;-&space;\hat{f}(x)\right)&space;\right]^2" title="https://latex.codecogs.com/svg.image?e_{\sigma}(f,\hat{f}) = \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left[ \left(f(x) - \hat{f}(x)\right) - \frac{1}{2^n} \sum_{x \in \mathbb{B}^n} \left(f(x) - \hat{f}(x)\right) \right]^2" />
 
### Defining your own error metric

In case the metric you want to use isn't available, you can define it on your own and make it available to ```pyALS``` through its dynamic module loader. This mechanism also allows you to simulate the behavior of the approximate component you want to design when deployed in a given target application.

#### Simple, generic metric

Suppose you want to define the worst-case relative error magniture metric  for error assessment, as defined above.

The procedure follows:
1. create a source file, namely ```relative_error_magnitude.py``` in the root directory of ```pyALS```; I suggest using a directory in which to place user-defined metrics, so, in the following, I suppose you have the ```custom_error_metrics``` directory in the root directory of ```pyALS```;
2. in the mentioned source file, implement the function computing the error metric; for instance, in the ```relative_error_magnitude.py``` you can put the following
    ```python
    import numpy as np
    
    def compute_rem(graph, input_data, configuration, weights):
        current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in input_data ]  #compute the output of the circuit for each of the samples
        rem = 0
        for sample, current in zip(input_data, current_outputs):
            f_exact = np.sum([float(weights[o]) * sample["output"][o] for o in weights.keys() ]) # compute f(x), from the circuit output
            f_apprx = np.sum([float(weights[o]) * current[o] for o in weights.keys() ])          # compute the same, but for the approximate circuit
            err = np.abs(1- f_apprx / f_exact)                                                   # computing the relative error 
            if rem < err:                                                                        # keeping track of the maximum 
                rem = err                                                                        
            return rem
    ```
   please note that, whatever metric you're going to compute, the function computing it ***MUST*** have the following parameters, in the specified order:
   1. ```graph```: graph-based representation of the circuit suitable for simulation; for now, consider it as a black box: you're only using it to obtain the circuit output for each input vector, using ```graph.evaluate(sample["input"], configuration) for sample in input_data```;
      1. ```input_data```: the input data to be used for error assessment; in this particular case it is a list of input vectors automatically generated by the tool; each entry of the list is a dictionary with two entries:
         - ```input```: a dictionary containing the truth value of each primary input signal; the value field for this key is a dictionary itself that can be indexed using PIs' name in order to get the corresponding truth value;
         - ```output```: a dictionary containing the truth value of each primary outsingal signal; the value field for this key is a dictionary itself that can be indexed using POs' name in order to get the corresponding truth value;

         for instance, consider a 4-input-4-output circuit with the following interface, coded in Verilog HDL
         ```
         module mult_2_bit (
            input  logic [1:0]  a,
            output logic [3:0]  o,
            input  logic [1:0]  b
         );
         ```
         the mentioned list of dictionary will be, depending on the number of input vectors to be generated, the set of PIs and POs, something like
         ```
         [
           {'input': {'\\a[0]': False, '\\a[1]': False, '\\b[0]': False, '\\b[1]': False}, 'output': {'\\o[0]': False, '\\o[1]': False, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': False, '\\a[1]': False, '\\b[0]': False, '\\b[1]': True}, 'output': {'\\o[0]': False, '\\o[1]': False, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': False, '\\a[1]': False, '\\b[0]': True, '\\b[1]': False}, 'output': {'\\o[0]': False, '\\o[1]': False, '\\o[2]': False, '\\o[3]': False}},
           {'input': {'\\a[0]': False, '\\a[1]': False, '\\b[0]': True, '\\b[1]': True}, 'output': {'\\o[0]': False, '\\o[1]': False, '\\o[2]': False, '\\o[3]': False}},
           {'input': {'\\a[0]': False, '\\a[1]': True, '\\b[0]': False, '\\b[1]': False}, 'output': {'\\o[0]': False, '\\o[1]': False, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': False, '\\a[1]': True, '\\b[0]': False, '\\b[1]': True}, 'output': {'\\o[0]': False, '\\o[1]': False, '\\o[2]': True, '\\o[3]': False}}, 
           {'input': {'\\a[0]': False, '\\a[1]': True, '\\b[0]': True, '\\b[1]': False}, 'output': {'\\o[0]': False, '\\o[1]': True, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': False, '\\a[1]': True, '\\b[0]': True, '\\b[1]': True}, 'output': {'\\o[0]': False, '\\o[1]': True, '\\o[2]': True, '\\o[3]': False}}, 
           {'input': {'\\a[0]': True, '\\a[1]': False, '\\b[0]': False, '\\b[1]': False}, 'output': {'\\o[0]': False, '\\o[1]': False, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': True, '\\a[1]': False, '\\b[0]': False, '\\b[1]': True}, 'output': {'\\o[0]': False, '\\o[1]': True, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': True, '\\a[1]': False, '\\b[0]': True, '\\b[1]': False}, 'output': {'\\o[0]': True, '\\o[1]': False, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': True, '\\a[1]': False, '\\b[0]': True, '\\b[1]': True}, 'output': {'\\o[0]': True, '\\o[1]': True, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': True, '\\a[1]': True, '\\b[0]': False, '\\b[1]': False}, 'output': {'\\o[0]': False, '\\o[1]': False, '\\o[2]': False, '\\o[3]': False}}, 
           {'input': {'\\a[0]': True, '\\a[1]': True, '\\b[0]': False, '\\b[1]': True}, 'output': {'\\o[0]': False, '\\o[1]': True, '\\o[2]': True, '\\o[3]': False}},
           {'input': {'\\a[0]': True, '\\a[1]': True, '\\b[0]': True, '\\b[1]': False}, 'output': {'\\o[0]': True, '\\o[1]': True, '\\o[2]': False, '\\o[3]': False}},
           {'input': {'\\a[0]': True, '\\a[1]': True, '\\b[0]': True, '\\b[1]': True}, 'output': {'\\o[0]': True, '\\o[1]': False, '\\o[2]': False, '\\o[3]': True}}
         ]

         ```
         you can obtain the circuit output for each input vector using ```graph.evaluate(sample["input"], configuration) for sample in input_data```; feel free to spawn processes, if you need them, to speed-up the computation; Furthermore,  ```pyALS``` is thought to be as flexible as possible, so you can pass the error-assessment function anything you want; for further details se the "Simulating a whole application" section below.

   2. ```configuration```: the approximate configuration to be evaluated; the only thing you have to know is you have to pass it to the ```evaluate``` method of the ```graph``` object;
   3. ```weights```: python dictionary containing weights for output signals, as specified in the JSON configuration file; with these, you can compute the numeric value of the output from using ```np.sum([float(weights[o]) * sample["output"][o] for o in weights.keys() ])```, for instance

3. now, you have to tell to the ```pyALS``` tool to use the function you defined; you can do it in the JSON configuration file, specifically using the ```metric``` field of the ```error``` section; basically, you have to specify the module name, the function name and the reduce operation to be performed; these information have to be placed in the JSON file as a python dictionary, as follows
   ```json
       "error" : {
           "metric" : {
              "module" : "applications/relative_error_magnitude", # the path to the module source file; note that the ```module``` field gives the path where the module is stored, but it does not have any "py" extension;
              "function" : "compute_rem"}                         # the actual name of the function to be called
       }
   ```


#### Simulating a whole application

```pyALS``` also allows you to approximate a component while considering its final application into account, using the same mechanism we exploited before to extend the set of error metrics.
To illustrate how it works, I'll consider a simple demo application, i.e., the approximation of a 16-bits signed fixed-point multiplier intended to be used in a FIR filter, using the PSNR as error metric to be minimized.
This example is also available in the ```example/fir``` directory of ```pyALS```.

First, let's implement the function computing the PSNR between a reference signal and the one computed using the approximate multiplier.
```python
def get_mse_psnr(a, b):
   assert len(a) == len(b), "Arrays must be equal in size"
   mse = np.mean([(x - y) ** 2 for x, y in zip(a, b)])
   if mse == 0:
      return mse, np.inf
   max_ab = np.max(np.concatenate((a, b)))
   psnr = 20 * np.log10(max_ab / np.sqrt(mse))
   return mse, psnr


def compute_psnr(graph, input_data, configuration, weights):
   reference_signal = input_data["reference_output"]
   output_signal = compute_fir(graph, input_data, configuration, weights)
   assert len(reference_signal) == len(output_signal), "Reference and output signals must be equal in size"
   output_signal = [float(x) for x in output_signal]
   _, psnr = get_mse_psnr(output_signal, reference_signal)
   return -psnr # the PSNR has to be MAXIMIZED to minimize the error
```
Almost nothing to be explained here, except the fact that input_data is not generated by ```pyALS```. Instead, it is a custom data structure (actually, a python dictionary), containing data read from a JSON file.
It is used to access the input signal to be filtered, the coefficients of the filter and the reference signal for error computation.
In order to compute the output signal of the filter using the approximate multiplier, the ```compute_psnr()``` calls the ```compute_fir()``` function, which is reported below.
```python
def compute_fir(graph, input_data, configuration, weights):
   input_signal = [FixedPoint(c, signed = True, m = m, n = n) for c in input_data["input_signal"]]
   filter_coefficients = [FixedPoint(c, signed = True, m = m, n = n) for c in input_data["filter_coefficients"]]
   len_i, len_c = len(input_signal), len(filter_coefficients)
   len_r = len_i + len_c - 1
   return [sum([multiply(graph, configuration, weights, input_signal[j - i - len_c], filter_coefficients[i]) for i in range(len_c)]) for j in range(len_c, len_r + 1)]
```
Again, almost nothing to be explainded here, except the fact that the ```fixedpoint``` python module is being used for fixed-point arithmetic, and the ```multiply()``` function being used to the actual multiplication, hiding the multiplier being used.
The implementation of such function is reported below.
```python
def multiply(graph, configuration, weights, a, b):
   bin_a, bin_b = f"{a:016b}"[::-1], f"{b:016b}"[::-1]
   input_assignment = { **{ f"\\a[{i}]": bin_a[i] == "1" for i in range(16) }, **{ f"\\b[{i}]": bin_b[i] == "1" for i in range(16) }}
   output_assignment = graph.evaluate(input_assignment, configuration)
   return np.sum([float(weights[o]) * output_assignment[o] for o in weights.keys()])
```
Basically, the first two lines build a proper input assignment for the multiplier, then the latter is fed to the graph object to compute the output.
The output of the graph must be interpreted as a 16-bits fixed point number with a specific Qm.n representation. In order to do so, the last line of the function performs the required conversion exploiting weights for POs, that are defined in the JSON configuration file.
The last thing to be done is to tell ```pyALS```everything needed using the JSON configuration file as follows.
```json
       "error" : {
           "metric" : {
              "module" : "example/fir/fir",             # the path to the module source file; note that the ```module``` field gives the path where the module is stored, but it does not have any "py" extension;
              "function" : "compute_psnr"},             # the actual name of the function to be called
           "dataset"      : "example/fir/dataset.json", # the path to the JSON file containing the data for the mentioned function
       }
   ```
The content of the JSON file defined using the ```dataset``` field will be passed ***as is*** to the ```compute_psnr()```.

## Manual installation

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




## References
1. Bandyopadhyay, S., Saha, S., Maulik, U., & Deb, K. (2008). A simulated annealing-based multiobjective optimization algorithm: AMOSA. IEEE transactions on evolutionary computation, 12(3), 269-283.
2. Blank, Julian, and Kalyanmoy Deb. "A running performance metric and termination criterion for evaluating evolutionary multi-and many-objective optimization algorithms." 2020 IEEE Congress on Evolutionary Computation (CEC). IEEE, 2020.
