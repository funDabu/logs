# Logs

This is a user guide. Here you can read more about the tool,
namely what is its [output](#output) look like, [how does it works](#how-are-logs-processed), what are the [requirements](#require)
and finaly an [exapmle](#example) of using this tool.

## Output {#output}

Multiple files are created as an output. These files are always created in current working directory.
Quick overview of these files follows,
but you can learn more about the output in commented example.

For each year in logs `YYYY.html` file is created which contains:
   - ovreview pictures illustrating hte count of requests, sessions or unique IP addresses for each day in the year
   - section for bots with following subsections:
      - tables of 20 most frequent IP addresses based on the count of requests or sessions
      - requests and sessions distribution across hours of a day illustrated by a table and graphs
      - requests and sessions distribution across days of a week illustrated by a table and graphs
      - requests and sessions distribution across months of the year illustrated by a table and graphs
   - section for non-bots with the same subsections, except an extra estimated locations subsection
     which contains a table and a graph depicting the results of geolocation on the sample.
     The displayed values are weigted by the session count of the located IP address, you can read about the geolocation [here](#geoloc).
     Please be aware, that in reality this section includes
     many bots which escaped the the simplified [bot classification](#bot-class).

The `hist.html` file which informs about the number of IP adresses with given count of requests or sessions.
For this output, only entires classified as non-bots are considered.
The files is devided into section each concerned with data from one year in the logs.
In each section, you can see:
   - Session or request histogram subsection including two histogram graphs,
     the second graph zooms into the first graph depicting only x-axis values less than 300.
     Then follows a table describing count of IPs 
     devided into bins based on their sessions or requests count.
   - Most frequent subsection which is identical to the mostfrequent subsection for non-bots in the `YYYY.html` files.

## How are logs processed

### Input access log format
The access log entry is expected to look like this:
```
127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"
```
That corresponds to apache [*Combined Log Format*](https://httpd.apache.org/docs/2.4/logs.html)
```
%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-agent}i\"
```
The entries should be provided in their time order, unless session detection will not work.


#### Input format in details
The log entries (log lines) are expected to contain log fields separated by a single space character.
Here follows a description of expected format of these log entry fields:

1. **IPv4 address or hostname** - Each log entry has to start with IPv4.
   Presence of a hostname instead of IPv4 is also possible,
   but these names has to be resolved back to IP,
   which is extremely time expensive process.
2. **RFC 1413 identity** - non-space string is expected.
   This information is not used later in the processing.
3. **user id** - non-space string is expected.
   This information is not used later in the processing.
4. **Time** - in following format:
```[day/month/year:hour:minute:second zone]```,
or more formaly in Python [datetime format](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes):
```%d/%b/%Y:%H:%M:%S %z```.
  So the time fiels is expected to look similar to this
  ```[10/Oct/2000:13:55:36 -0700]```.
5. **Request line** - a string in closed in quotes is expected.
   This information is not used later in the processing.
6. **Status code** - non-space string is expected.
   This information is not used later in the processing.
7. **Size of returned object** - non-space string is expected.
   This information is not used later in the processing.
8. **Referer** - a string in closed in quotes is expected,
   backslash can be used as an escape character.
   This information is not used later in the processing.
9. **User agent** - a string in closed in quotes is expected,
   backslash can be used as an escape character.
   This information is used for classification of bots.

## Processing pipeline

### 1. Parsing

All logs from the input are parsed.
This is done using [Python regex](https://docs.python.org/3/library/re.html) search.

### 2. Log details processing {#processing}

Each parsed log entry goes through this porocess
  - **Fields count checking** - if the count of fields if different from nine,
   then this entry is skipped 
  - **Time parsing**
  - **New session detection** - if the time from previous request from the same IP address is 
  is more than one minute, this request is conssidered as a new session.
  Note that this is the main reason,
  why input log entries should be time ordered.
  The more there are breaks in the time ordering of input log entries,
  the greater count of mis-detection of new sessions will be.
  - **Bot classification** - see [bot classification](#bot-class).

Then, base on the entry details, statistical details of the log are update.
These statistical details are saved separately for every year in the log
and for bots and non-bots.
Following information is stored:
  - requests and sessions count for each IP addresss
  - requests and sessions count in each hour of day
  - requests and sessions count in each day of a week
  - requests and sessions count in each month in the given year

Additionaly, for entries not classified as bots, the count of requests and sessions in each day,
and a set of unique IPs in each day, are stored for each day in the log.

### 3. Hostname to IP resolution {#ip_res}

So far it was expected that all IP fields contains IPv4.
Hovewer, that is sometimes not the case and this field contains hostname instead.
Beacuse of this issue, all stored details are check
whether those field which should contain an IP address contains 
something that looks like one.
If not, the content of this field is considered as a hostname and 
resolution of the corresponding IP address is made.
During this porocess hostname with multiple IP adresess can emerge.
If that happens, the IP which is most frequent (based no sessions) in the log
for given hostname is selected.

Note that this is a time expensive process and no parallelization is used.
In other words, it is not realistic to expect results from this program
if the log contains hunderts or even thousands different hostnames instead of IPs.

### 4. Grouping bots data on url

Amongs data classified as bots, there can be multiple data with differen IP address but with same bot URL,
which is a URL than can somtimes be found in the *user agent* log entry field.
These are considered as same "type" of bot and are group together, so there so
there is only one entry with given URL in processed data.
During the aggregation, the IP address for the resulting data entry is selected the one with most request count in the logs.

### 5. Output files creation

In this stage, both output pictures and html files are created.
This process includes IP to hostname resolutions for table entries in html files,
and a geolocation of these table entries and of a sample providing 
geolocation information about the log as whole.

### Bot classification {#bot-class}

Log etnries are calsified as bots based on the *User agent* field content.
If it contains an URL, or a sepcified substing is found in it,
then the entry is considered as a bot. Otherwise as a non-bot.

The specific substrings currently used for bot detection is defined by following regex:
```bot|Bot|crawl|Crawl|GoogleOther```.
Note that this is far from exhaustive bot detection,
even when considering just those bots, which doesn't hide themselves
and can be recognized by the *User agent* field.
If you find frequent bot in your logs identifing itself with a different substring,
you can always edit the source code, namely the `BOT_USER_AGENT_REGEX` variable
in `logs/statistics/constants.py`.

### Geolocation {#geoloc}

For geolocation [geoplugin](https://www.geoplugin.com/) API is used. Beacuse the access to the API
is limited, only 3 request to the API per 2 second are made at the maximum rate.
Thus it impossible to geolocate all IPs in the log. To sove this issue,
a sample of unique IP addresses with a default size 1000 is selected randomly
from IPs in given year and geolocation made on the sample.

To account for the different frequency of each IP address from the sample in the log,
the geolocation value is weigheted by the sessions count of the IP address.
That poses another issue: sometimes an IP address with an exeptionaly high sessions count 
is seleced into the sample and beacuse of the session-based weighting
the geolocation values of other IP adresses become insignificant in comparasion to this value.
This situation is fixed by selecting into the sample only IP addresses with session count less than 50.
For the logs which this program is originaly intended for, the count if IPs with sessions count exceeding 50 is less then 1 %.
If you want to see how many IPs follows this criterion, look into the tables in `hist.html` output file.


### Cache

The cache is loaded before [log details processing](#processing) and is saved after [IP address resolution](ip_res).
The case is stored in the direcotry specified by the `-c` or `--cache` option.
If you use this options, only those entries older than the `timestamp` in the cache (see below)
undergo the [log details processing](#processing) and are added to loaded data from cache.
If you want to process data younger than the `timestamp`, you have to 
remove all cached data starting from the year of the data you want to process,
manually set the timestamp accordingly, and then re-process all the logs
older than the new timestamp. Or you can remove all the cache a re-process
all from scratch.

The cache is quite human readable and has following structure: 
in the directory specified by the `-c` option a `logcache` directory is created if not exists,
which will store all the cache files:
   - `timestamp` - file containing unix timestamp of the oldest proccess log entry
   - `YYYY-bot_distrib_file` and `YYYY-human_distrib_file` which contain on each line following information (in this oreder):
      - day requests distribution
      - day sessions distribution
      - week requests distribution
      - week sessions distribution
      - month requests distribution
      - month sessions distribution
   - `YYYY-bot_stats_file` and `YYYY-human_stats_file` containg details about each IP address,
   the order of the details is:
      - ip address
      - hostname
      - geolocation
      - bot url
      - is bot (True/False)
      - requests count
      - sessions count
      - time
      - valid ip (True/False)
   - `daily_data_file` - containing:
      - date
      - unique IPs count
      - requests count
      - sessions count
   - `timestamp` - containing unix timestamp of the oldest cached log entry 
     and its human readable form.

### Processing speed

## Requirements {#require}

### PIP

- certifi==2023.11.17
- charset-normalizer==2.0.12
- cycler==0.11.0
- idna==3.6
- kiwisolver==1.3.1
- matplotlib==3.3.4
- numpy==1.19.5
- Pillow==8.4.0
- pyparsing==3.1.1
- python-dateutil==2.8.2
- requests==2.27.1
- six==1.16.0
- urllib3==1.26.18

### Python

- tested with Python 3.6



### How to use
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
  -U, --group_url       Disable grouping bots on url
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


### Example

You can see example of using this script [here](./example.md)