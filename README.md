# nlp-logs


### Usage of logs.py
Usage: logs.py [options]

Options:
  -h, --help            show this help message and exit
  -i INPUT, --input=INPUT
                        Specify the path to input log file which will be
                        procces; if not specified, standar input will be taken
                        as input.When equal to '-' no input is will be parsed,
                        only data from cache of json might be used.When used
                        together with -l, --load or -c, --cache options, only
                        entries older than loaded timestamp will be
                        proccessed.
  -n NAME, --name=NAME  Specify name of the porccessed log. Name will be
                        diplayed output files
  -e, --error           log execution details to stderr
  -g GEOLOC_SAMPLE, --geolocation=GEOLOC_SAMPLE
                        sample size for geolocation
  -c CACHE, --cache=CACHE
                        specify the path to the directory where the cache
                        direcory is located. Data from chache will be loaded,
                        then merged together with proccessed data, and then
                        saved to the chache.If used together with -l, --load
                        option, no cache will be loaded, but will be saved.
  -b BOT_CONFIG, --bot_config=BOT_CONFIG
                        Specify the path of the bot configuration file. That
                        is plain text file, containing just an IPv4 on each
                        line.Ip addresses from the config file will be
                        clasified as bots.
  -d GEOLOC_DB, --geoloc_database=GEOLOC_DB
                        Specify the path of geolocation database. This is
                        SQLite database used for saving resolved geolocations
  -y YEARS, --year=YEARS
                        Restrict generated output to given years. If not
                        given, than all output for each present year will be
                        generated. Use value '-' if you do not want to
                        generate output for any year.The restriction woun't
                        apply to the general index html and the general
                        overview pictures without the usage of -Y,
                        --just_years option.
  -Y, --just_years      Restrict to given years also the content of the
                        general index html and general overview pictures. To
                        specify the years use -y, --year option.
  -H, --no_histogram    Make no html file 'hist.html' with histograms. Note
                        that histograms would ideally need some improvements2.
  -P, --no_picture      Don't make overview pictures
  -I, --no_index        Do not generate html index file
  -s JSON_OUT, --save=JSON_OUT
                        Specify a name of a json file, which proccessed log
                        statisics will be exported to
  -l JSON_IN, --load=JSON_IN
                        Specify a json file, which proccessed statiscics will
                        be loaded from. When used together with -c, --cache
                        flag, no cache will be loaded
  -t TEST, --test=TEST  Test geolocation, specify number of repetitions.


### Fully process any log

```sh
cd location/where/output/will/be/created
cat log/file/path <...> log/file/path | python/venv/path/python3 path/to/logs.py -g<INT> -n<STRING> [-c<PATH>] [-d<PATH>] [-e]
```

Arguments for options:
- *-g\<INT\>* - geolocation sample size
- *-n\<STRING\>* - name of the log
- *-c\<PATH\>* - path to "cache"
- *-d\<PATH\>* - path to SQLite database file
    containing geoloacations for ip addresses

The output files (.html, .png) will be created in *CWD*.

Note that when cache for the log already exists,
data loaded from cache will be combined with the processed log from input.
However, in such case, `logs.py` can only process from input logs younger than the last entry in cache (timestamp).
The script will ignore entries older than the timestamp.
In other words, if you need to re-process already processed logs,
you have to remove the cache and recreate all from scratch.