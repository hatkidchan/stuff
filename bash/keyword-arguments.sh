#!/bin/bash
# I've attempted to implement keyword-arguments in BASH
# Idunno why, but.. Yes.
declare -A kwargs=();  # Associative array for keyword-arguments
declare args=();       # Regular array for positional arguments

for arg in "$@"; do    # So, we're iterating over bash arguments
    if echo $arg | grep -P "\w+\=.*" >/dev/null; then  # If it looks like kwarg
        IFS='=' read key value <<< $arg;  # Split key and value
        kwargs[$key]=$value;  # And assign key
    else  # if it's not
        arg=$(echo -n $arg | sed 's/\\=/=/g');  # Remove escaped "="
        args+=($arg);  # and append to array
    fi;
done;

# We're done! Here we're just printing all args
for i in "${!args[@]}"; do
    echo "args[$i] = ${args[$i]}";
done;

for key in "${!kwargs[@]}"; do
    echo "kwargs[$key] = ${kwargs[$key]}";
done;

