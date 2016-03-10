# ST Shell

A commandline based tool which enables you to:

* List all your custom SmartApps / DeviceType Handlers
* Show files belonging to your SmartApp / DeviceType Handler
* Create new SmartApps / DeviceType Handlers
* Upload files to existing SmartApps / DeviceType Handlers
* Delete files from existing SmartApps / DeviceType Handlers
* Delete entire SmartApps / DeviceType Handlers
* Download all or parts of a SmartApp / DeviceType Handler
* Update files in existing SmartApps / DeviceType Handlers

# Requirements

You must have `requests` installed (`pip install requests`)

For improved console (CTRL-R, etc) you can install readline:
* OSX: `pip install gnureadline`
* Win: `pip install pyreadline`
* Linux: Should work out-of-the-box

# Usage

Please see `stshell -h` for the most accurate an up-to-date explaination of options.

# Notes

The `console` option is VERY new and is prone to break, right now it can traverse the entire server tree in a FTP like fashion. It implements `ls` and `cd` and soon `get`. It comes with a built-in help, just type `help`
