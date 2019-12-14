#!/bin/bash

shopt -s nullglob
for i in *.csv;
do
    echo "$i"
    python3 digest.py $i
done