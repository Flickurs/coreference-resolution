#!/bin/bash
chmod +x getenv.sh
./getenv.sh
if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters"
else
    ./virtual_env/bin/pip install -r requirements.txt
    ./virtual_env/bin/python -m spacy.en.download all
    ./virtual_env/bin/python coreference.py $1 $2
fi
