import os
import subprocess
import sys
import re
import json
import math

import json
  
dataset_file = open('dataset.json')
dataset = json.load(dataset_file)
open("dataset-eval.json", "w").write(json.dumps(dataset[0:len(dataset)//500], indent=2))
open("dataset-train.json", "w").write(json.dumps(dataset[len(dataset)//500:], indent=2))
dataset_file.close()