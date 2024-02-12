# nlp-logs


### Usage of logs.py
- Reads the log from stdin (unless -l option is used)
- creates the output files in CWD

Options:
-  -h, --help
    - show this help message and exit
-  -g \<INT\>, --geolocation=\<INT\>
    - specify sample size for geolocation
-  -e, --error
    - print execution details to stderr
-  -T \<INT\>, --test=\<INT\>
    - test geolocation, specify number of repetitions
-  -y \<INT\>, --year=\<INT\>
    - prints log statistics of given year to std.out
-  -s \<PATH\>, --save=\<PATH\>
    - export the program data as json, specify path of the export file
-  -n \<STRING\>, --name=\<STRING\>
    - specify the name of the log.
    Name will become the heading of the logs_index.html file
-  -l \<PATH\>, --load=\<PATH\>
    - load the exported program data from json,
    specify the name of the file
-  -H, --histogram
    - makes html file 'hist.html' with histograms
-  -p, --pictureoverview
    - makes picture overview
-  -c, --clean
    - when no --year is given and --clean is set,
    then no charts are made.
    Good for use together with --test, --histogram or --pictureoverview
-  -i, --ignore
    - ignore data from std input,
    has to be used together with --load option
-  -C \<PATH\>, --config=\<PATH\>
    - specify the path of configuration file,
    ip addresses in config file will be clasified as bots
-  -d \<PATH\>, --geoloc-database=\<PATH\>
    - specify the path of geolocation database

### Fully process any log
`cat <log PATH> | python3 <PATH>logs.py -g<INT> -n<STRING> -H -p [-C<PATH>] [-d<PATH>] [-e]`

Arguments for options:
- *-g\<INT\>* - geolocation sample size
- *-n\<STRING\>* - name of the logfile
- *-C\<PATH\>* - path to configuration file
    containing bot ip adresses
- *-d\<PATH\>* - path to SQLite database file
    containing geoloacations for ip addresses

The output files (.html, .png) will be created in CWD