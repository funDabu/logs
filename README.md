# Logs
This is a tool for creating simple statistics from apache access logs.

## Description

This tool is designed to process access logs into human readable statitical information about the log.
It is a lighweight program not using any database engine, requiring only Python 3 and few python packages (see [requirements](#require)).

The program takes as its input access logs in plain text, parses and processes it,
and makes html files and pictures containg statistical information about the log.
Processed logs can be saved into human readable "cache",
so later logs can be processed without processing the these already processed logs.


## Features

- Primitive [bot detection](bot-class)
- [Geolocation](geoloc)
- [Output](#output) html file with tables and graphs containg simple statistical information about the log 

## User guide
More information is provided [here](./docs/guide.md).