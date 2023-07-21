import os
import subprocess
import sys
import re
import json


directory = sys.argv[1]

INSTRUCTION = "Create commentary for the following game of go in SGF format."
dataset = []
METADATA_REGEX = re.compile(r'((BR|WR|KM|RE|SZ)\[.+\])')
MOVE_AND_COMMENTS_REGEX = re.compile(r'((;(W|B|)\[.*?\])|(\n(M|C)(\[(.|\n)*?\])+))')
TOP_SCORE_DROP_REGEX = re.compile(r'(?<=score drops: )(#[0-9]{0,3} ⇣[0-9]{1,2}\.[0-9]{1,2}%?(, )?)+')

for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith(".sgf"):
            try:
                cleaned_original = subprocess.check_output(['./sgf', directory+file]).decode('utf-8')
                main_variation = subprocess.check_output(['./get-main-var.sh', directory+file]).decode('utf-8')
                analyzed_file_name = directory+"analyzed/main-var" + file
                with open(analyzed_file_name, "w").write(main_variation) as mainvar_file:
                    mainvar_file.write(main_variation)
                subprocess.call(['analyze-sgf',  analyzed_file_name])
                with open(analyzed_file_name, "r") as analyzed:
                    analyzed_game = analyzed.decode('utf-8')
                # score_drops = "".join(TOP_SCORE_DROP_REGEX.findall(analyzed_game)).split("#")
                # score_drops = [drop.split(" ") for drop in score_drops]


                metadata_main_variation = ';'+''.join([item[0] for item in METADATA_REGEX.findall(main_variation)])
                moves_and_comments_main_variation = [item[0] for item in MOVE_AND_COMMENTS_REGEX.findall(main_variation)]

                moves = "".join([item for item in moves_and_comments_main_variation if item[0] == ';'])
                comments_with_node_index = [(index,item) for index, item in enumerate(moves_and_comments_main_variation) if item[0] == '\n']
                comments_with_move_number = [(item[0] - index,item[1]) for index, item in enumerate(comments_with_node_index)]
                comments = "".join([str(move_number) + "|" + comment[1:] for move_number, comment in comments_with_move_number])
            except:
                print("failed" + directory+file + ", continuing..")
            else:
                if moves and comments:
                    dataset.append({"instruction": INSTRUCTION, "input": metadata_main_variation + moves, "output": comments})
                if len(dataset) % 100 == 0:
                    print("just did file number:" + str(len(dataset)) + ", named: " + file)

# Serializing json
json_array = json.dumps(dataset, indent=2)
 
# Writing to sample.json
with open("dataset.json", "w") as outfile:
    outfile.write(json_array)