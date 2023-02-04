#!/bin/bash
export PYTHONUNBUFFERED=1
# Given a list of languages supported in Lingua Libre (list_languages.txt),
# and a wiki-specific script name (${wiki_project}),
# adds missing recording to that targeted wiki.

# Useful when a new wiki project is supported by
# Lingua Libre Bot in order to add all audio that have
# been recorded in the past

# Define target project
wiki_project="kuwiktionary"

# Loop on languages supported by lingualibre
while read langcode; do
#    if [ "${langcode}" != "Q21" ]; then
#       continue
#    fi
    
    echo "Processing ${langcode}"
    if [ "${langcode}" = "Q21" ] ||      # French
           [ "${langcode}" = "Q298" ] || # Polish
           [ "${langcode}" = "Q307" ];   # Bengali
    then
        # French language has too many recordings
        # so splitting the request is required
        # we ask for recordings for every year
        current_year=`date +%Y`
        for year in `seq 2017 ${current_year}`; do
            for month in 01 07; do
                startdate="${year}-${month}-01T00:00:00.000+00:00"
		
		month_end="01"
		if [ ${month} = "01" ]; then
		    month_end="07"
		fi
		year_end=${year}
		if [ ${month_end} = "01" ]; then
                    year_end=$((${year}+1))
		fi
		   
                enddate="${year_end}-${month_end}-01T00:00:00.000+00:00"
                echo "start: ${startdate}, end: ${enddate}"
               $HOME/venv/bin/python3 -u $HOME/Lingua-Libre-Bot/llbot.pyy --wiki ${wiki_project} simple --lang ${langcode} --startdate ${startdate} --enddate ${enddate}
		# sleep 5 seconds to avoid Error 429 Too Many Requests
		sleep 5
            done
        done
    else
        $HOME/venv/bin/python3 -u $HOME/Lingua-Libre-Bot/llbot.py --wiki ${wiki_project} simple --lang ${langcode}
    fi
    
    # sleep 5 seconds to avoid Error 429 Too Many Requests
    sleep 5
done <list_languages.txt
echo "DONE"

