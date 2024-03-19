# Example

In this file we illustrate the usage of this tool in step by step fashion.
 
## Initial situation
Suppose there are access logs in acceptable format in `/var/logs/apache2/YYYY-MM-example.log` files,
the path to `logs.py` script is `/path/to/logs.py` and 
the path to venv with installed required PIP packages is `/path/to/venv`.

## Process logs from 2023
Let's say the output should be created in `/some/dir/for/output` directory
and there is already a database of geolocation results at `/path/to/geolocation/db`
Then we will proceed as follows

```sh
cd /some/dir/for/output
cat /var/logs/apache2/2023-MM-example | /path/to/venv/bin/python3 /path/to/logs.py -e -n example_log -c . -d /path/to/geolocation/db 
```

Now we will explain the used script options.
Because the `-i` or `--input` option is not used, input logs are read from standard input.
We use `-e` option to swich on verbose mode, in which the program will write into error output what task is being currently done. Next we use `-c .` option, to create a cache,
which will enable us to add new logs to this output without parsing all from beginning.
Finally we use `-d /path/to/geolocation/db` to idicate the path to geolocation database.
New database is created, if is not found. If you don't intent to use this script regurarly,
you don't have create the database, in such scenario simply don't use the `-d` option at all.

The error output may look like follows:
```
Task 'Logs.py' has started.
Task 'loading cache' has started.
Task 'loading cache' has finished, duration: 0.0 seconds
Task 'Data parsing and proccessing' has started.
Task 'Data parsing and proccessing' has finished, duration: 7785.01 seconds
Task 'IPs resolving and merging' has started.
Task 'IPs resolving and merging' has finished, duration: 3525.77 seconds
Task 'saving cache' has started.
Task 'saving cache' has finished, duration: 28.26 seconds
Task 'creating output html files' has started.
Task 'making charts of bots and human users' has started.
Task 'making charts of bots and human users' has finished, duration: 8.72 seconds
Task 'geolocation' has started.
Task 'geolocation' has finished, duration: 488.66 seconds
Task 'creating output html files' has finished, duration: 497.38 seconds
Task 'creating overview pictures' has started.
Task 'creating overview pictures' has finished, duration: 5.38 seconds
Task 'creating histograms' has started.
Task 'creating histograms' has finished, duration: 42.18 seconds
Task 'Logs.py' has finished, duration: 11884.0 seconds
```

Now when we display the content of current directory, we should be able to see
`logs_index.html`, `2023.html`, `hist.html` files, some *.png* files and 
`logchache` directory.

## Process logs from the beginnigng of 2024

Now we would like to add to the output also logs from frist months of 2024.
Processing the logs for year 2023 took more than 3 hours, so we would like
to only process the data from 2024. Beacuse we have created the cache for year 2023
we can do that, we can process just the new data and then created output files from 
both cache and the new data. We will achive this by:

```sh
cd /some/dir/for/output
cat /var/logs/apache2/2024-01-example | /path/to/venv/bin/python3 /path/to/logs.py -e -n example_log -c . -d /path/to/geolocation/db 
```

The error output may look like follows:
```
Task 'Logs.py' has started.
Task 'loading cache' has started.
Task 'loading cache' has finished, duration: 28.32 seconds
Task 'Data parsing and proccessing' has started.
Task 'Data parsing and proccessing' has finished, duration: 637.51 seconds
Task 'IPs resolving and merging' has started.
Task 'IPs resolving and merging' has finished, duration: 301.39 seconds
Task 'saving cache' has started.
Task 'saving cache' has finished, duration: 29.26 seconds
Task 'creating output html files' has started.
Task 'making charts of bots and human users' has started.
Task 'making charts of bots and human users' has finished, duration: 7.84 seconds
Task 'geolocation' has started.
Task 'geolocation' has finished, duration: 455.76 seconds
Task 'making charts of bots and human users' has started.
Task 'making charts of bots and human users' has finished, duration: 8.16 seconds
Task 'geolocation' has started.
Task 'geolocation' has finished, duration: 480.03 seconds
Task 'creating output html files' has finished, duration: 951.79 seconds
Task 'creating overview pictures' has started.
Task 'creating overview pictures' has finished, duration: 5.68 seconds
Task 'creating histograms' has started.
Task 'creating histograms' has finished, duration: 67.84 seconds
Task 'Logs.py' has finished, duration: 2021.79 seconds
```

Now new `2024.html` file has appeard in the current folder.
Note that `2023.html` file was also recreated. If you want to supress this behavior, 
create only `2024.html` and update `logs_index.html` and related overview pictures
use `-y` or `--year` option:
```sh
cat /var/logs/apache2/2024-01-example | /path/to/venv/bin/python3 /path/to/logs.py -e -n example_log -c . -d /path/to/geolocation/db -y 2024
```

## Example output

You can see example output [here](https://html-preview.github.io/?url=https://github.com/funDabu/logs/blob/public/docs/example_output/logs_index.html)
