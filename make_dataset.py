import os
import subprocess
import sys
import re
import json
import glob

INSTRUCTION = "Create commentary for the following game of go in SGF format."
METADATA_REGEX = re.compile(r'((BR|WR|KM|RE|SZ)\[.+\])')
MOVE_AND_COMMENTS_REGEX = re.compile(r'((;(W|B|)\[.*?\])|(\n(M|C)(\[(.|\n)*?\])+))')
SCORE_DROP_REGEX = re.compile(r'(?<=\* Score drop: ).+')
DROP_CLEAN_REGEX = re.compile(r'-?[0-9]+\.?[0-9]+')
KEEP_DIVIDER = 1.8
INSTRUCTION_DROP_ESTIMATOR = "This is a game of go in SGF format, estimate the score drop for the " +str(round((1/1.8)*100))+ "% most impactful moves."

from multiprocessing import Lock, Process, Queue, current_process
import time
import queue # imported for using queue.Empty exception

def convert_paralel(tasks_to_accomplish, tasks_that_are_done):
    while True:
        try:
            '''
                try to get task from the queue. get_nowait() function will 
                raise queue.Empty exception if the queue is empty. 
                queue(False) function would do the same task also.
            '''
            task = tasks_to_accomplish.get_nowait()
        except queue.Empty:
            break
        else:
            '''
                if no exception has been raised, add the task completion 
                message to task_that_are_done queue
            '''
            dir, file, analyze_only = task
            convert(dir, file, analyze_only)
            tasks_that_are_done.put(str(task) + ' is done by ' + current_process().name)
    return True

def paralel_analyze(directory, number_of_processes=4):
    tasks_to_accomplish = Queue()
    tasks_that_are_done = Queue()
    processes = []

    for path in glob.iglob(directory + '**/*.sgf', recursive=True):
        directory, file = os.path.split(path) 
        tasks_to_accomplish.put((directory+"/", file, True))

    # creating processes
    for w in range(number_of_processes):
        p = Process(target=convert_paralel, args=(tasks_to_accomplish, tasks_that_are_done))
        processes.append(p)
        p.start()

    # completing process
    for p in processes:
        p.join()

    # print the output
    while not tasks_that_are_done.empty():
        print(tasks_that_are_done.get())
    return True

def make_dataset():
    directory = sys.argv[1]
    analyze_only = sys.argv[2] if len(sys.argv) >= 4 else False

    if analyze_only:
        paralel_analyze(directory = sys.argv[1], number_of_processes = int(sys.argv[3]))
    else:
        dataset = []
        for path in glob.iglob(directory + '**/*.sgf', recursive=True):
            directory, file = os.path.split(path) 
            if 'analyzed' in directory:
                continue
            moves_with_drops, output, moves = convert(directory+"/", file)

            if moves_with_drops and output:
                dataset.append({"instruction": INSTRUCTION, "input": input, "output": output})
            if moves and not output:
                dataset.append({"instruction": INSTRUCTION_DROP_ESTIMATOR, "input": moves, "output": moves_with_drops})
            if len(dataset) % 100 == 0:
                print("just did file number:" + str(len(dataset)) + ", named: " + file)

        json_array = json.dumps(dataset, indent=2)
        with open("dataset.json", "w") as outfile:
            outfile.write(json_array)

def convert(directory, file, analyze_only=False):
    try:
        main_variation = subprocess.check_output(['./get-main-var.sh', directory+file]).decode('utf-8')
        metadata_main_variation = extract_metadata(main_variation)
        score_drops = analyze(directory+"analyzed/main-var-" + file, main_variation)
        if analyze_only:
            return
        moves_with_drops, comments, moves = extract_moves_and_comments(main_variation, score_drops)
    except Exception as error:
        print("failed" + directory+file + ", continuing..")
        print("An error occurred:", error) 
        return "", "", ""
    else:
        return metadata_main_variation + moves_with_drops, comments, metadata_main_variation + moves
    
def analyze(analyzed_file_name, main_variation, analyze_only=False):
    if not os.path.isfile(analyzed_file_name):
        os.makedirs(os.path.dirname(analyzed_file_name), exist_ok=True)
        with open(analyzed_file_name, "w") as mainvar_file:
            mainvar_file.write(main_variation)    
        subprocess.call(['analyze-sgf',  analyzed_file_name], stdout=subprocess.DEVNULL)
    if analyze_only:
        return
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
