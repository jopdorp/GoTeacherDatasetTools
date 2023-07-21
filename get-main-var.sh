#!/bin/bash

FILE=$1

./sgfvarsplit -v 1 $FILE
./sgf < ./var-001.sgf
rm ./var-001.sgf