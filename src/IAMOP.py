"""
Copyright 2021-2023 Salvatore Barone <salvatore.barone@unina.it>

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
import itertools, pyamosa, numpy as np, copy, json5, pandas as pd
from pyalslib import list_partitioning, negate, flatten
from multiprocessing import cpu_count, Pool
from .HwMetrics import *
from .ErrorMetrics import *
from tqdm import tqdm
from .MOP import MOP

class IAMOP(MOP):
    
    def __init__(self, top_module, graph, output_weights, catalog, error_config, hw_config, ncpus, dataset):
        MOP.__init__(self, top_module, graph, output_weights, catalog, error_config, hw_config, ncpus)
        self.dataset = dataset
        
    def init(self):
        lut_io_info = self.load_dataset()
        self._setup_mop(lut_io_info)
        
    def load_dataset(self):
        print(f"Reading input data from {self.dataset} ...")
        if self.dataset.endswith(".json") or self.dataset.endswith(".json5"):
            return self.load_dataset_json()
        elif self.dataset.endswith(".csv") or self.dataset.endswith("."):
            return self.load_dataset_spreasheet()
    
    def load_dataset_json(self):
        self.samples = json5.load(open(self.dataset))
        PIs = set(pi["name"] for pi in self.graph.get_pi())
        lut_io_info = {}
        self.error_config.n_vectors = len(self.samples)
        print(f"Read {self.error_config.n_vectors} test vectors.")
        for sample in tqdm(self.samples, desc = "Checking input-vectors...", bar_format="{desc:40} {percentage:3.0f}% |{bar:60}{r_bar}{bar:-10b}"):
            assert PIs == set(sample["input"].keys())
            output, lut_io_info = self.graph.evaluate(sample["input"], lut_io_info)
            assert sample["output"] == output, f"\n\nRead output:\n{sample['output']}\n\nComputed output:\n{output}\n"
        return lut_io_info
    
    def load_dataset_spreasheet(self):
        dataframe = pd.read_csv(self.dataset, sep = ';') if self.dataset.endswith(".csv") else pd.read_excel(self.dataset)
        column_names = dataframe.columns.values.tolist()
        PIs = set(pi["name"] for pi in self.graph.get_pi())
        assert all(c in PIs for c in column_names), f"Columns mismatches! Expected: {PIs}, got {column_names}"
        lut_io_info = {}
        self.error_config.n_vectors = len(dataframe)
        print(f"Read {self.error_config.n_vectors} test vectors.")
        samples = dataframe.to_dict(orient='records')
        self.samples = []
        for sample in tqdm(samples, desc = "Checking input-vectors...", bar_format="{desc:40} {percentage:3.0f}% |{bar:60}{r_bar}{bar:-10b}"):
            output, lut_io_info = self.graph.evaluate(sample, lut_io_info)
            self.samples.append({"input": sample, "output": output})
        return lut_io_info

        
        
        

    