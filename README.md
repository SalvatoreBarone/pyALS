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
pyALS supports the following main commands, each with its own set of options:
  - ```als```: performs the full catalog-based AIG-rewriting workflow, including cut enumeration, exact synthesis of approximate cuts, design space exploration and rewriting;
  - ```es```: performs the catalog-based AIG-rewriting workflow until catalog generation, i.e., including cut enumeration, and exact synthesis of approximate cuts, but it performs neither the design space exploration phase not the rewriting;
  - ```plot```: only draws the k-LUT map of the given circuit;

Please kindly note you will need the file where synthesized Boolean functions are stored, i.e., the catalog-cache file. 
You can mine, which is ready-to-use, frequently updated and freely available at ```git@github.com:SalvatoreBarone/pyALS-lut-catalog```.
If you do not want to use the one I mentioned, pyALS will perform exact synthesis when needed.

Furthermore, the ```als``` and ```es``` commands requires a lot of configuration parameters, which are provided through a JSON configuration file. Therefore,
we will first discuss the generic structure of the latter, before going into command-specific information.

### The configuration file
The configuration file defines parameters governing the behavior of pyALS. Is is a JSON file which generic structure is reported below.
Please note that, depending on the specific command you selected, some parameters are not required, hence they can be omitted.
Furthermore, an example configuration file is provided in the ```example``` directory.

In the following, each field of the JSON file is described using C-Style comments. Note JSON does not provide any support for comments, hence you must remove them in case you copy-and-paste from the following box.

```json
{
    "hdl" : {
        "source" : "example/mult_2_bit.sv",             // the HDL source file
        "top"    : "mult_2_bit",                        // the top-level entity name
        "output" : "results"                            // path to the output directory
    },
    "als" : {
        "cache"    : "lut_catalog.db",                  // path to the catalog-cache
        "cut_size" : 4,                                 // specifies the "k" for AIG-cuts, or, alternatively, the k-LUTs for LUT-mapping during cut-enumeration, always required
        "solver"   : "btor",                            // SAT-solver to be used. It can be either btor (Boolector) or z3 (Z3-solver), always required
        "timeout"  : 60000                              // Timeout (in ms) for the exact synthesis process, always required. It is better you don't change its default value.              
    },
    "error" : {                                         // This section defines error-related stuff
        "metric"       : "med",                         // Error metric to be used during Design-Space exploration. It can be "ep", "awce" or "med", for error-probability, absolute worst-case error or mean error distance, respectively; The "ia-ep" and "ia-ed" stand for "input-aware" error-probability and error-distance, which require the user to provide the probability-distribution for input vectors  
        "threshold"    : 16,                            // The error threshold
        "vectors"      : 5,                             // The number of test vectors for error assessment. Using the value "0" will unlock exhaustive evaluation, i.e., it will cause the tool to evaluate the error for every possible input assignment.
        "distribution" : "input_distribution.csv",      // Input distribution file required for both the "ia-ep" and "ia-ed" metrics, in csv or json
        "weigths" : {                                   // specify weights for outputs, as needed by the AWCE, MED and IA-MED metrics
            "\\o[0]" : 1,
            "\\o[1]" : 2,
            "\\o[2]" : 4,
            "\\o[3]" : 8
        }
    },
    "hardware]" : {                                     // Hardware related stuff
        "metric" : ["gates", "depth", "switching"]      // hardware metric(s) to be optimized (AIG-gates, AIG-depth, or LUT switching activity). Please note you can specify more than one metric.
    },
    "amosa" : {                                         // Parameters governing the Archived Multi-Objective Simulated-Annealing optimization heuristic 
        "archive_hard_limit"       : 100,               // Archive hard limit for the AMOSA optimization heuristic, see [1]
        "archive_soft_limit"       : 200,               // Archive soft limit for the AMOSA optimization heuristic, see [1]
        "archive_gamma"            : 2,                 // Gamma parameter for the AMOSA optimization heuristic, see [1]
        "hill_climbing_iterations" : 500,               // the number of iterations performed during the initial hill-climbing refinement, see [1];
        "initial_temperature"      : 500,               // Initial temperature of the matter for the AMOSA optimization heuristic, see [1]
        "final_temperature"        : 0.0000001,         // Final temperature of the matter for the AMOSA optimization heuristic, see [1]
        "cooling_factor"           : 0.95,              // It governs how quickly the temperature of the matter decreases during the annealing process, see [1]
        "annealing_iterations"     : 750,               // The amount of refinement iterations performed during the main-loop of the AMOSA heuristic, see [1]
        "annealing_strength"       : 1,                 // Governs the strength of random perturbations during the annealing phase; specifically, the number of variables whose value is affected by perturbation.
        "early_termination"        : 20                 // Early termination window. See [2]. Set it to zero in order to disable early-termination. Default is 20.
    }
}
```

## Error metrics

pyALS actually provides the user to define the error metric to be used during optimization. It can be selected through the ```metric``` field of the ```error``` section of the configuration file.
The latter can be set to "ep", "awce" or "med", for error-probability, absolute worst-case error or mean error distance, respectively, which are defined below.

<img src="https://render.githubusercontent.com/render/math?math=e_{prob}(f,\hat{f})=\frac{1}{2^n} \sum_{\forall x \in \mathbb{B}^n} \llbracket f(x) \ne \hat{f}(x) \rrbracket">
<br>
<img src="https://render.githubusercontent.com/render/math?math=e_{awce}(f,\hat{f})=\max_{\forall x \in \mathbb{B}^n} |int(f(x)) - int(\hat{f}(x))|">
<br>
<img src="https://render.githubusercontent.com/render/math?math=e_{med}(f,\hat{f})=\sum_{\forall x \in \mathbb{B}^n} |int(f(x)) - int(\hat{f}(x))| \cdot P(|int(f(x)) - int(\hat{f}(x))|)">

### Defining your own error metric

In case the metric you want to use isn't available, you can define it on your own and make it available to ```pyALS``` through its dynamic module loader.
Suppose you want to define the relative error magniture (REM) metric  for error assessment, as defined below.
<br>
<img src="https://render.githubusercontent.com/render/math?math=e_{rem}(f,\hat{f}) = max_{\forall x \in \mathbb{B}^n} \left| 1 - \frac{\hat{f}(x)}{f(x)} \right|">

The procedure follows: 
1. create a source file, namely ```relative_error_magnitude.py``` in the root directory of ```pyALS```; I suggest using a directory in which to place user-defined metrics, so, in the following, I suppose you have the ```custom_error_metrics``` directory in the root directory of ```pyALS```;
2. in the mentioned source file, implement the function computing the error metric; for instance, in the ```relative_error_magnitude.py``` you can put the following 
    ```python
    import numpy as np
    
    def compute_rem(graph, samples, configuration, weights):
        current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]  #compute the output of the circuit for each of the samples
        rem = 0
        for sample, current in zip(samples, current_outputs):
            f_exact = np.sum([float(weights[o]) * sample["output"][o] for o in weights.keys() ]) # compute f(x), from the circuit output
            f_apprx = np.sum([float(weights[o]) * current[o] for o in weights.keys() ])          # compute the same, but for the approximate circuit
            err = np.abs(1- f_apprx / f_exact)                                                   # computing the relative error 
            if rem < err:                                                                        # keeping track of the maximum 
                rem = err                                                                        
            return rem
    ```
   please note that, whatever metric you're going to compute, the function computing it ***MUST*** have the following parameters, in the specified order:
   1. ```graph```: graph-based representation of the circuit suitable for simulation; for you it is a black box, and you're only using it to obtain the circuit output for each input vector, using ```graph.evaluate(sample["input"], configuration) for sample in samples```;
   2. ```samples```: the input vectors to be used for error assessment (actually, a fraction of them); these are generated by ```pyALS```; It is an array-like of dictionaries with two entries, i.e., ```input``` and ```output```; the latter are dictionaries indexed using the name of primary inputs and primary output signals;
   3. ```configuration```: the approximate configuration to be evaluated; the only thing you have to know is you have to pass it to the ```evaluate``` method of the ```graph``` object;
   4. ```weights```: python dictionary containing weights for output signals, as specified in the JSON configuration file; with these, you can compute the final error, if it has arithmetic meaning;

    please, note that the ```samples``` parameter is only a fraction of the set of input vectors used for error assessment. This is because the error assessment is performed using python multiprocessing.function you define will be performed. This is why you have to specify the **reduction operator** to be used; it can be either ```sum``` or ```max```; in this case, the latter is appropriate. 
3. now, you have to tell to the ```pyALS``` tool to use the function you defined; you can do it in the JSON configuration file, specifically using the ```metric``` field of the ```error``` section; basically, you have to specify the module name, the function name and the reduce operation to be performed; these information have to be placed in the JSON file as a python dictionary, as follows
   ```json
       "error" : {
           "metric" : {"module" : "applications/relative_error_magnitude", "function" : "compute_rem", "reduce": "max"}  
       }
   ```
   note that the ```module``` field gives the path where the module is stored, but it does not have any "py" extension; furthermore, once again, please note that the error assessment is performed using python multiprocessing, in parallel, using all the available cores provided by the machine.

## Command line interface

You can use the following commands

### The ```plot``` command
Draws a k-LUT map of the given circuit

Usage: 
```
pyALS plot [OPTIONS]
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

### The ```dataset``` command
Creates a CSV template file to be used to define a  

Usage: 
```
pyALS dataset [OPTIONS]
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



### The ```es``` command
Performs the catalog-based AIG-rewriting workflow until catalog generation, i.e., including cut enumeration, and exact synthesis of approximate cuts, but it performs neither the design space exploration phase not the rewriting.

Usage: 
```
pyALS es [OPTIONS]
```
Options:
```
  --config TEXT  path of the configuration file
```
Example:
```
./pyALS es --config /path_to_config.json 
```


### The ```als``` command
Performs the full catalog-based AIG-rewriting workflow, including cut enumeration, exact synthesis of approximate cuts, design space exploration and rewriting.

Usage: 
```
pyALS als [OPTIONS]
```
Options:
```
  --config TEXT   path of the configuration file
  --improve TEXT  Run again the workflow using previous Pareto set as initial archive
  --resume        Resume the execution. It searches for available checkpoints in the output directory.
```
Example:
```
./pyALS als --source /path_to_source --top top_level_entity --catalog /path_to_catalog_cache --output /path_to_output_directory --config /path_to_config.json --improve /path_to_final_archive.json --resume 
```



## Manual installation

The guide has been tested on Debian 11.

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
You're almost done, the last step is to install python dependencies. It's quite simple, and you just need to issue the following command from within the pyALS directory.
```bash
pip3 install -r requirements.txt 
```




## References
1. Bandyopadhyay, S., Saha, S., Maulik, U., & Deb, K. (2008). A simulated annealing-based multiobjective optimization algorithm: AMOSA. IEEE transactions on evolutionary computation, 12(3), 269-283.
2. Blank, Julian, and Kalyanmoy Deb. "A running performance metric and termination criterion for evaluating evolutionary multi-and many-objective optimization algorithms." 2020 IEEE Congress on Evolutionary Computation (CEC). IEEE, 2020.
