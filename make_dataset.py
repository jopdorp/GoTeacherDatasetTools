import os
import subprocess
import sys
import re
import json


INSTRUCTION = "Create commentary for the following game of go in SGF format."
METADATA_REGEX = re.compile(r'((BR|WR|KM|RE|SZ)\[.+\])')
MOVE_AND_COMMENTS_REGEX = re.compile(r'((;(W|B|)\[.*?\])|(\n(M|C)(\[(.|\n)*?\])+))')
SCORE_DROP_REGEX = re.compile(r'(?<=\* Score drop: ).+')
DROP_CLEAN_REGEX = re.compile(r'-?[0-9]+\.?[0-9]+')
KEEP_DIVIDER = 1.8
INSTRUCTION_DROP_ESTIMATOR = "This is a game of go in SGF format, estimate the score drop for the " +str(round((1/1.8)*100))+ "% most impactful moves."

def make_dataset():
    directory = sys.argv[1]
    dataset = []
    for _, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".sgf"):
                moves_with_drops, output, moves = convert(directory, file)
                if moves_with_drops and output:
                    dataset.append({"instruction": INSTRUCTION, "input": input, "output": output})
                if moves and not output:
                    dataset.append({"instruction": INSTRUCTION_DROP_ESTIMATOR, "input": moves, "output": moves_with_drops})
                if len(dataset) % 100 == 0:
                    print("just did file number:" + str(len(dataset)) + ", named: " + file)
        break

    json_array = json.dumps(dataset, indent=2)
    with open("dataset.json", "w") as outfile:
        outfile.write(json_array)

def convert(directory, file):
    try:
        main_variation = subprocess.check_output(['./get-main-var.sh', directory+file]).decode('utf-8')
        metadata_main_variation = extract_metadata(main_variation)
        score_drops = analyze(directory+"analyzed/main-var-" + file, main_variation)
        moves_with_drops, comments, moves = extract_moves_and_comments(main_variation, score_drops)
    except Exception as error:
        print("failed" + directory+file + ", continuing..")
        print("An error occurred:", error) 
        return "", ""
    else:
        return metadata_main_variation + moves_with_drops, comments, metadata_main_variation + moves
    
def analyze(analyzed_file_name, main_variation):
    if not os.path.isfile(analyzed_file_name):
        os.makedirs(os.path.dirname(analyzed_file_name), exist_ok=True)
        with open(analyzed_file_name, "w") as mainvar_file:
            mainvar_file.write(main_variation)    
        subprocess.call(['analyze-sgf',  analyzed_file_name], stdout=subprocess.DEVNULL)
    
    with open(analyzed_file_name, "r") as analyzed:
        analyzed_game = analyzed.read()
    score_drops = SCORE_DROP_REGEX.findall(analyzed_game)
    score_drops = [clean_drop(drop) for drop in score_drops]
    return keep_large_drops(score_drops, False)

def clean_drop(drop):
    return float(DROP_CLEAN_REGEX.findall(drop)[0])
    
def keep_large_drops(score_drops, keep_all=True):
    score_drops = list(enumerate(score_drops))
    score_drops.sort(key=lambda x: abs(x[1]))
    score_drops = [ (drop[0], ( drop[1] if index > len(score_drops)//KEEP_DIVIDER or keep_all else 0)) for index, drop in enumerate(score_drops)]
    score_drops.sort(key=lambda x:x[0])
    return [ str(drop) if abs(drop) > 0 else '' for _, drop in score_drops]

def extract_comments(moves_and_comments_main_variation, moves):
    comments_with_node_index = [(index,item) for index, item in enumerate(moves_and_comments_main_variation) if item[0] == '\n']
    comments_with_move_number = [(item[0] - index,item[1]) for index, item in enumerate(comments_with_node_index)]
    return ''.join([str(move_number) + "|" + comment[1:] if moves[move_number-1][-1] != ']' else '' for move_number, comment in comments_with_move_number])

def extract_metadata(main_variation):
    return ';'+''.join([item[0] for item in METADATA_REGEX.findall(main_variation)])

def extract_moves_and_comments(main_variation, score_drops):
    moves_and_comments_main_variation = [item[0] for item in MOVE_AND_COMMENTS_REGEX.findall(main_variation)]
    moves = [item[1:].replace('tt', '') for item in moves_and_comments_main_variation if item[0] == ';']

    moves_with_drops = [ ''.join(move) for move in zip(moves[0:len(score_drops)], score_drops)]
    comments = extract_comments(moves_and_comments_main_variation, moves_with_drops)
    return ';' + ';'.join([str(i + 1) + '#' + move if move[-1] != ']' else move for i, move in enumerate(moves_with_drops)]), comments, ';'.join(moves)

make_dataset()