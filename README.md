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

It also provides a console option, which I will talk about a bit more

# Console option

Yes, you read that right, this tool can essentially give you an emulated console
to the SmartThings back-end. It strives to be ftp like in its behavior and many
of the commands are inspired from this.

Currently, the console mode implements the following commands:

### cd [&lt;directory&gt;]
Changes the current directory or displays the current directory

### ls [&lt;directory&gt;]
Lists the contents of the current directory or the provided one

### lcd [&lt;directory&gt;]
Same as cd but acts upon the local directory of your terminal

### lls [&lt;directory&gt;]
Same as ls but acts upon the local directory of your terminal

### lmkdir &lt;directory&gt;
Creates a directory on your local terminal

### get &lt;file|folder&gt;
Downloads a file or a complete folder (with subfolders) to your current local directory

### put &lt;file&gt;
Uploads a file to the current directory. If the file already exists, it's updated.

### mput &lt;pattern&gt;
Uploads one or more files (depending on pattern) to the current directory. Should any file already exist, it's updated.

### rm &lt;file&gt;
Deletes a file from the current directory.

### mrm &lt;pattern&gt;
Deletes zero or more file(s) from the current directory based on the provided pattern.

### rmmod &lt;directory&gt;
Deletes the entire SmartApp or DeviceTypeHandler. This command requires user to acknowledge the operation since it's very dangerous.

### create &lt;local groovy file&gt;
Creates a SmartApp or a DeviceTypeHandler based on the provided groovy file.

### publish &lt;directory&gt;
Publishes the smartapp or devicetypehandler to which the directory belongs. For short, you can use `.` as the directory name if the current path is within a modules.

## Caveats

* The console option does not deal gracefully with multiple smartapps or devicetypehandlers named the EXACT SAME THING, so please avoid or use the commandline options instead.

* There is no `rmdir` for the server, this is intentionally, since folders are virtual. If no file exists in a folder, they are automatically removed. The console mode emulates a directory structure so it may show empty folders, but they will most likely not show up on the WebIDE.

* Using relative paths and/or absolute paths is mostly supported where possible, but don't get upset if it fails

* TAB completion only works on commands for now, eventually it will work for filenames/paths but it's very low priority.

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
