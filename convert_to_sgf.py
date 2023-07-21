import os
import subprocess
import sys
import re
import json

  
game_file = open('game.json')
game = json.load(game_file)
game_file.close()

moves = game["moves"].split(";")

commentary = game["comments"]
move_numbers = re.compile(r'([0-9]*\|)').findall(commentary)
comments = re.compile(r'(\|(M|C)(\[(.|\n)*?\])+)').findall(commentary)
move_indexed_comments = zip(move_numbers, comments)

comments_per_move_dict = {}
for key, value in move_indexed_comments:
    comments_per_move_dict.setdefault(int(key[:-1]), []).append(value[0][1:])


commented_game = "(;" + ";".join(
            [
                move + "".join(comments_per_move_dict[index] if index in comments_per_move_dict else []) 
                for index, move in enumerate(moves)
            ]
        ) + ")"

open('game.sgf', 'w').write(commented_game)