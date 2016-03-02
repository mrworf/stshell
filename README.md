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

# Usage

`usage: stshell.py [-h] [--username EMAIL] [--password PASSWORD]
                  [--server SERVER]
                  type action [options [options ...]]`

`--username` is your login to smartthings<br>
`--password` is the password<br>
These two can be stored in ~/.stshell in a key/value pair format<br>
`--server` allows you to override the default graph.api.smartthings.com with whatever you want<br>
`type` should be either `smartapp` or `devicetype` and determines what the action acts upon

`action` must be one of the following:

* `list`
Lists all smartapps or devicetypes with their associated UUID
* `contents <UUID>`
Shows the contents of a smartapp or devicetype, including the UUIDs for each entry
* `download <UUID>`
Downloads the entire smartapp or devicetype into your current folder
* `download <UUID> <UUID>`
Downloads a part of a smartapp or devicetype into your current folder, use `contents` to get the second UUID
* `delete <UUID>`
Deletes an entire smartapp or devicetype. Will ask for confirmation before proceeding
* `delete <UUID> <ITEM>`
Deletes an item from the smartapp or devicetype. Will ask for confirmation before proceeding
* `create <groovy file>`
Creates a new smartapp or devicetype using the provided groovy file
* `upload <UUID> <TYPE> <PATH> <FILE>`
Uploads the FILE into smartapp or devicetype identified by UUID and tells the server it's TYPE and should be placed in the sub-directory of PATH. PATH can be an empty string "" to indicate root of folder. TYPE should be one of the following:
** IMAGE
** VIEW
** JAVASCRIPT
** I18N
** CSS
** OTHER
and will give an error if you try something else.

The tool will automatically detect conflicts and refuse to upload a file which would overwrite an existing file.

* `update <UUID> <UUID> <FILE>
Updates an item in a smartapp or devicetype with the contents in FILE. Use `contents` to get the second UUID
If the update fails, it will print out why.

# Notes

Work in progress, still not able to update the groovy code, but that's next on the list.