#!/bin/bash
export PYTHONUNBUFFERED=1
# Loop over all languages supported in Lingua Libre
# and add missing recording to the targeted wiki

# Useful when a new wiki project is supported by
# Lingua Libre Bot in order to add all audio that have
# been recorded in the past
wiki_project="kuwiktionary"

while read langcode; do
    echo "Processing ${langcode}"
    if [ "${langcode}" = "Q21" ]; then
        # French language has too many recordings
        # so splitting the request is required
        # we ask for recordings for every year
        current_year=`date +%Y`
        for year in `seq 2017 ${current_year}`; do
            startdate="${year}-01-01T00:00:00.000+00:00"
            year=$((${year}+1))
            enddate="${year}-01-01T00:00:00.000+00:00"
            #echo "start: ${startdate}, end: ${enddate}"
            $HOME/venv/bin/python3 -u $HOME/Lingua-Libre-Bot/llbot.py --wiki ${wiki_project} simple --lang Q21 --s\
				   tartdate ${startdate} --enddate ${enddate}
        done
    fi

    $HOME/venv/bin/python3 -u $HOME/Lingua-Libre-Bot/llbot.py --wiki kuwiktionary simple --lang ${langcode}
    # sleep 5 seconds to avoid Error 429 Too Many Requests
    sleep 5
done <list_languages.txt
echo "DONE"
