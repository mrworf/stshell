#!/usr/bin/env python
#
# Copyright 2016 Henric Andersson
#
# The base for a shell like interface to your smartthings account,
# allowing the following:
#
# - Create SA/DTH
# - Upload of individual files to SA/DTH
# - Download of individual files and complete SA/DTH
# - Delete of individual files or complete SA/DTH
#

import argparse
import requests
import json
import re
import os
import sys

class STServer:
    TYPE_SA = 1
    TYPE_DTH = 2

    UPLOAD_TYPE = {
        'OTHER'     : 'other',
        'IMAGE'     : 'images',
        'CSS'       : 'css',
        'I18N'      : 'i18n',
        'JAVASCRIPT': 'javascript',
        'VIEW'      : 'view'
    }

    URL_PATH = {}
    URL_PATH['login'] = '/j_spring_security_check'
    URL_PATH['smartapps'] = '/ide/apps'
    URL_PATH['smartapp-resources'] = '/ide/app/getResourceList'
    URL_PATH['smartapp-download'] = '/ide/app/getCodeForResource'
    URL_PATH['smartapp-create'] = '/ide/app/saveFromCode'
    URL_PATH['smartapp-upload'] = '/ide/app/uploadResources'
    URL_PATH['smartapp-editor'] = '/ide/app/editor/'
    URL_PATH['smartapp-delete'] = '/ide/app/deleteResource'
    URL_PATH['smartapp-destroy'] = '/ide/app/delete/'
    URL_PATH['smartapp-update'] = '/ide/app/compile'

    URL_PATH['devicetypes'] = '/ide/devices'
    URL_PATH['devicetype-resources'] = '/ide/device/getResourceList'
    URL_PATH['devicetype-download'] = '/ide/device/getCodeForResource'
    URL_PATH['devicetype-upload'] = '/ide/device/uploadResources'
    URL_PATH['devicetype-editor'] = '/ide/device/editor/'
    URL_PATH['devicetype-delete'] = '/ide/device/deleteResource'
    URL_PATH['devicetype-create'] = '/ide/device/saveFromCode'
    URL_PATH['devicetype-destroy'] = '/ide/device/update'

    def __init__(self, username, password, baseUrl):
        self.URL_BASE = baseUrl
        self.USERNAME = username
        self.PASSWORD = password
        self.session = requests.Session()

    def resolve(self, type=None):
        if type is None:
            return self.URL_BASE
        return "%s/%s" % (self.URL_BASE, self.URL_PATH[type])

    def login(self):
        post = {"j_username" : self.USERNAME, "j_password" : self.PASSWORD}
        r = self.session.post(self.resolve("login"), data=post, cookies={})
        if r.status_code == 200 and "JSESSIONID" in self.session.cookies.keys():
            return True
        print "ERROR: Failed to login"
        return False

    def listSmartApps(self):
        """
        " Returns a hashmap with the ID of the app as key and the name and namespace
        """
        r = self.session.post(self.resolve("smartapps"))
        if r.status_code != 200:
            print "ERROR: Failed to get smartapps list"
            return None

        apps = re.compile('\<a href="/ide/app/editor/([^"]+)".*?\>\<img .+?\>\s*(.+?)\s*:\s*(.+?)\</a\>', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        lst = apps.findall(r.text)

        result = {}
        if lst is not None:
            for i in lst:
                result[i[0]] = {'id' : i[0], 'namespace' : i[1], 'name' : i[2]}
        return result

    def listDeviceTypes(self):
        """
        " Returns a hashmap with the ID of the app as key and the name and namespace
        """
        r = self.session.post(self.resolve("devicetypes"))
        if r.status_code != 200:
            print "ERROR: Failed to get smartapps list"
            return None

        apps = re.compile('\<a href="/ide/device/editor/([^"]+)".*?\>\s*(.+?)\s*:\s*(.+?)\</a\>', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        lst = apps.findall(r.text)

        result = {}
        if lst is not None:
            for i in lst:
                result[i[0]] = {'id' : i[0], 'namespace' : i[1], 'name' : i[2]}
        return result

    def __lister__(self, details, path, lst):
        for d in details:
            if "id" in d.keys():
                lst[d["id"]] = path + "/" + d["text"]
            elif "children" in d.keys():
                lst = self.__lister__(d["children"], path + "/" + d["text"], lst)
        return lst

    def getFileDetails(self, path, uuid):
        """ Returns a list of files contained in this smartapp """
        r = self.session.post(self.resolve(path), params={"id" : uuid})
        if r.status_code != 200:
            return None

        lst = self.__lister__(r.json(), "", {})

        return {"details" : r.json(), "flat" : lst }

    def getSmartAppDetails(self, smartapp):
        """ Returns a list of files contained in this smartapp """
        return self.getFileDetails("smartapp-resources", smartapp)

    def getDeviceTypeDetails(self, devicetype):
        """ Returns a list of files contained in this devicetype """
        return self.getFileDetails("devicetype-resources", devicetype)

    def __digger__(self, details, uuid, path):
        result = None
        for d in details:
            if "id" in d.keys() and d["id"] == uuid:
                return {"filename" : d["text"], "type" : d["li_attr"]["resource-type"], "content" : d["li_attr"]["resource-content-type"], "path" : path}
            elif "children" in d.keys():
                result = self.__digger__(d["children"], uuid, path + "/" + d["text"])

            if result is not None:
                break

        return result

    def getDetail(self, details, uuid):
        """ Builds a path and extracts the necessary parts to successfully download an item """
        info = self.__digger__(details, uuid, "")
        return info

    def downloadItem(self, path, owner, details, uuid):
        """ Downloads the selected item and returns it """
        details = self.getDetail(details, uuid)
        if details is None:
            print "ERROR: Unable to get details of item"
            return None

        r = self.session.post(self.resolve(path), params={"id" : owner, "resourceId" : uuid, "resourceType" : details["type"]})
        if r.status_code != 200:
            print "ERROR: Unable to download item"
            return None

        details["data"] = r.content
        return details

    def createSmartApp(self, content):
        payload = {"fromCodeType" : "code", "create" : "Create", "content" : content}
        r = self.session.post(self.resolve("smartapp-create"), data=payload, allow_redirects=False)
        if r.status_code != 302:
            print "ERROR: Unable to create item"
            return None

        p = re.compile('.*/ide/app/editor/([a-f0-9\-]+)', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        m = p.match(r.headers["Location"])

        return m.group(1)

    def updateSmartAppItem(self, details, smartapp, uuid, content):
        details = self.getDetail(details, uuid)
        payload = {"code" : content, "location" : "", "id" : smartapp, "resource" : uuid, "resourceType" : details["type"]}
        r = self.session.post(self.resolve("smartapp-update"), data=payload)
        if r.status_code != 200:
            print "ERROR: Unable to update item"
            return None

        return r.json()


    def deleteSmartApp(self, uuid):
        r = self.session.get(self.resolve("smartapp-destroy") + uuid, allow_redirects=False)
        if r.status_code == 302:
            return True
        return False

    def getSmartAppIds(self, uuid):
        r = self.session.get(self.resolve("smartapp-editor") + uuid)
        """
        ST.AppIDE.init({
                            url: '/ide/app/',
                            websocket: 'wss://ic.connect.smartthings.com:8443/',
                            client: '1af9e4e7-9a2d-47a4-9edf-c9f326642489',
                            id: '19d2016d-2337-46bc-ae0e-143e033d4a63',
                            versionId: '5d01fb38-cd7f-48b3-be2f-2509efb09020',
                            state: 'NOT_APPROVED'
                        });
        """

        p = re.compile('ST\.AppIDE\.init\(\{.+?url: \'([^\']+)\',.+?websocket: \'([^\']+)\',.+?client: \'([^\']+)\',.+?id: \'([^\']+)\',.+?versionId: \'([^\']+)\',.+?state: \'([^\']+)\'', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        m = p.search(r.text)

        if m:
            return {
                "url" : m.group(1),
                "websocket" : m.group(2),
                "client" : m.group(3),
                "id" : m.group(4),
                "versionid" : m.group(5),
                "state" : m.group(6)
            }
        return None

    """ Uploads content to server, needs special uuid which is not same as app uuid """
    def uploadSmartAppItem(self, uuid, content, filename, path, kind):
        files = {"fileData" : (filename, content)}
        data = {
            "id" : uuid,
            "file-type|" + filename : kind,
            "file-path|" + filename : path,
            "uploadResource" : "Upload"
        }

        r = self.session.post(self.resolve("smartapp-upload"), data=data, files=files)
        if r.status_code == 200:
            return True
        return False

    def deleteSmartAppItem(self, uuid, item):
        r = self.session.post(self.resolve('smartapp-delete'), data={"id" : uuid, "resourceId" : item})
        if r.status_code == 200:
            return True
        return False

    def getDeviceTypeIds(self, uuid):
        r = self.session.get(self.resolve("devicetype-editor") + uuid)
        p = re.compile('ST\.DeviceIDE\.init\(\{.+?url: \'([^\']+)\',.+?websocket: \'([^\']+)\',.+?client: \'([^\']+)\',.+?id: \'([^\']+)\'', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        m = p.search(r.text)

        if m:
            return {
                "url" : m.group(1),
                "websocket" : m.group(2),
                "client" : m.group(3),
                "id" : m.group(4),
                "versionid" : m.group(4), # Same as Id for some reason
                "state" : None
            }
        return None

    def uploadDeviceTypeItem(self, uuid, content, filename, path, kind):
        files = {"fileData" : (filename, content)}
        data = {
            "id" : uuid,
            "file-type|" + filename : kind,
            "file-path|" + filename : path,
            "uploadResource" : "Upload"
        }

        r = self.session.post(self.resolve("devicetype-upload"), data=data, files=files)
        if r.status_code == 200:
            return True
        return False

    def deleteDeviceTypeItem(self, uuid, item):
        r = self.session.post(self.resolve('devicetype-delete'), data={"id" : uuid, "resourceId" : item})
        if r.status_code == 200:
            return True
        return False

    def createDeviceType(self, content):
        payload = {"fromCodeType" : "code", "create" : "Create", "content" : content}
        r = self.session.post(self.resolve("devicetype-create"), data=payload, allow_redirects=False)
        if r.status_code != 302:
            print "ERROR: Unable to create item"
            return None

        p = re.compile('.*/ide/device/editor/([a-f0-9\-]+)', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        m = p.match(r.headers["Location"])

        return m.group(1)

    def deleteDeviceType(self, uuid):
        payload = {"id" : uuid, "_action_delete" : "Delete"}
        r = self.session.post(self.resolve('devicetype-destroy'), data=payload, allow_redirects=False)
        if r.status_code == 302:
            return True
        return False

    def downloadSmartAppItem(self, smartapp, details, uuid):
        return self.downloadItem("smartapp-download", smartapp, details, uuid)

    def downloadDeviceTypeItem(self, devicetype, details, uuid):
        return self.downloadItem("devicetype-download", devicetype, details, uuid)

    # Convenience, downloads an entire smartapp
    def downloadBundle(self, kind, uuid, dest):
        print "Downloading bundle..."
        if kind == STServer.TYPE_SA:
            data = self.getSmartAppDetails(uuid)
        elif kind == STServer.TYPE_DTH:
            data = self.getDeviceTypeDetails(uuid)
        else:
            print "ERROR: Unsupported type"
            return False

        try:
            os.makedirs(dest)
        except:
            pass
        for i in data["flat"]:
            sys.stdout.write("  Downloading " + i + ": ")
            if kind == STServer.TYPE_SA:
                content = self.downloadSmartAppItem(uuid, data["details"], i)
            elif kind == STServer.TYPE_DTH:
                content = self.downloadDeviceTypeItem(uuid, data["details"], i)
            if content is None:
                print "Failed"
            else:
                filename = dest + content["path"] + "/" + content["filename"]
                print "OK (%s)" % content["filename"]
                try:
                    os.makedirs(dest + content["path"])
                except:
                    pass
                with open(filename, "wb") as f:
                    f.write(content["data"])
        return True

    def downloadSmartApp(self, uuid, dest):
        return self.downloadBundle(self.TYPE_SA, uuid, dest)

    def downloadDeviceType(self, uuid, dest):
        return self.downloadBundle(self.TYPE_DTH, uuid, dest)

def ArgType(value):
    value = value.lower()
    if value == "smartapp" or value == "sa":
        return False
    if value == "device" or value == "devicetype" or value == "dt" or value == "dth":
        return True
    raise argparse.ArgumentTypeError("Value must be smartapp or devicetype")

def ArgAction(value):
    accepted = ["list", "contents", "download", "create", "upload", "delete", "update"]
    value = value.lower()
    for x in accepted:
        if x == value:
            return x
    raise argparse.ArgumentTypeError("Value must be one of " + repr(accepted))

parser = argparse.ArgumentParser(description="ST Shell - Command Line access to SmartThings WebIDE", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--username', '-u', metavar="EMAIL", help="EMail used for logging into WebIDE")
parser.add_argument('--password', '-p', help="Password for the account")
parser.add_argument('--server', default="graph.api.smartthings.com", help="Change server to connect to")
parser.add_argument('type', type=ArgType, help="Choose what to operate on (smartapp or devicetype)")
parser.add_argument('action', type=ArgAction, help='One of "list", "contents", "download"')
parser.add_argument('options', nargs='*', help="Zero or more arguments depending on action")
cmdline = parser.parse_args()

cfg_username = cmdline.username
cfg_password = cmdline.password

# Try loading the settings
try:
    with open(os.path.expanduser('~/.stshell'), "r") as f:
        p = re.compile('([^=]+)=(.+)')
        for line in f:
            m = p.match(line)
            if m:
                if m.group(1) == "username":
                    cfg_username = m.group(2).strip()
                elif m.group(1) == "password":
                    cfg_password = m.group(2).strip()
                else:
                    print "Unknown parameter: %s" % (m.group(0))
except:
    pass

if cfg_username is None or cfg_password is None:
    print "ERROR: Username and password cannot be empty"
    sys.exit(255)

srv = STServer(cfg_username, cfg_password, "https://" + cmdline.server)
srv.login()

if cmdline.action == "list":
    # Lists all SA or DTHs
    if cmdline.type: # DTH
        types = srv.listDeviceTypes()
    else:
        types = srv.listSmartApps()
    for t in types.values():
        print "%36s | %s : %s" % (t["id"], t["namespace"], t["name"])
elif cmdline.action == "contents":
    # Shows the files inside a SA/DTH
    if cmdline.type: # DTH
        contents = srv.getDeviceTypeDetails(cmdline.options[0])
    else:
        contents = srv.getSmartAppDetails(cmdline.options[0])
    for k,v in contents["flat"].iteritems():
        print "%36s | %s" % (k, v)
elif cmdline.action == "download":
    # Downloads an entire bundle or just a single
    # item if a 2nd argument is provided
    uuid = cmdline.options[0]
    if len(cmdline.options) == 2: # We are downloading an item from a bundle
        item = cmdline.options[1]
    else:
        item = None

    if cmdline.type: # DTH
        if item:
            contents = srv.getDeviceTypeDetails(uuid)
            data = srv.downloadDeviceTypeItem(uuid, contents["details"], item)
            with open("./" + data["filename"], "wb") as f:
                f.write(data["data"])
        else:
            srv.downloadDeviceType(uuid, "./")
    else:
        if item:
            contents = srv.getSmartAppDetails(uuid)
            data = srv.downloadSmartAppItem(uuid, contents["details"], item)
            with open("./" + data["filename"], "wb") as f:
                f.write(data["data"])
        else:
            srv.downloadSmartApp(uuid, "./")
elif cmdline.action == "create":
    # Creates a new project, requires a groovy file
    with open(cmdline.options[0], "rb") as f:
        data = f.read()

    if cmdline.type: # Devicetype
        result = srv.createDeviceType(data)
        if result:
            print "DeviceType Handler %s created" % result
        else:
            print "Failed to create DeviceType Handler"
    else:
        result = srv.createSmartApp(data)
        if result:
            print "SmartApp %s created" % result
        else:
            print "Failed to create SmartApp"
elif cmdline.action == "delete":
    # Deletes an ENTIRE bundle, will prompt before doing so
    if cmdline.type: #DTH
        contents = srv.listDeviceTypes()
    else:
        contents = srv.listSmartApps()
    if not cmdline.options[0] in contents:
        print "ERROR: No such item"
        sys.exit(255)
    else:
        content = contents[cmdline.options[0]]

    if len(cmdline.options) == 1:
        sys.stderr.write('Are you SURE you want to delete "%s : %s" (yes/NO) ? ' % (content["namespace"], content["name"]))
        sys.stderr.flush()
        choice = sys.stdin.readline().strip().lower()
        if choice == "yes":
            sys.stderr.write("Deleting: ")
            sys.stderr.flush()
            if cmdline.type: #DTH
                srv.deleteDeviceType(cmdline.options[0])
            else:
                srv.deleteSmartApp(cmdline.options[0])
            sys.stderr.write("Done\n")
        else:
            sys.stderr.write("Aborted\n")
    elif len(cmdline.options) == 2:
        if cmdline.type:
            contents = srv.getDeviceTypeDetails(cmdline.options[0])
        else:
            contents = srv.getSmartAppDetails(cmdline.options[0])

        if not cmdline.options[1] in contents["flat"]:
            print "ERROR: No such item in bundle"
            sys.exit(255)
        sys.stderr.write('Are you SURE you want to delete "%s" from "%s : %s" (yes/NO) ? ' % (contents["flat"][cmdline.options[1]], content["namespace"], content["name"]))
        sys.stderr.flush()
        choice = sys.stdin.readline().strip().lower()
        if choice == "yes":
            sys.stderr.write("Deleting: ")
            sys.stderr.flush()
            if cmdline.type: #DTH
                srv.deleteDeviceTypeItem(cmdline.options[0], cmdline.options[1])
            else:
                srv.deleteSmartAppItem(cmdline.options[0], cmdline.options[1])
            sys.stderr.write("Done\n")
        else:
            sys.stderr.write("Aborted\n")


elif cmdline.action == "upload":
    # Uploads a file into a bundle: <uuid> <type> <path> <filename>

    uuid = cmdline.options[0]
    kind = cmdline.options[1].strip().upper()
    path = cmdline.options[2].strip()
    filename = cmdline.options[3]
    # Load content and change filename into the basename
    with open(filename, "rb") as f:
        data = f.read()
    filename = os.path.basename(filename)

    if kind not in STServer.UPLOAD_TYPE:
        print "ERROR: Only certain types are supported: " + repr(STServer.UPLOAD_TYPE)
        sys.exit(255)

    # Download the list of files so we don't try to overwrite (which won't work as you'd expect)
    if cmdline.type: #DTH
        details = srv.getDeviceTypeDetails(uuid)
    else:
        details = srv.getSmartAppDetails(uuid)

    prospect = "/%s/%s/%s" % (STServer.UPLOAD_TYPE[kind], path, filename)
    p = re.compile('/+')
    prospect = p.sub('/', prospect)

    if prospect in details["flat"].values():
        print 'ERROR: "%s" already exists. Cannot replace/update files using upload action' % prospect
        sys.exit(255)

    sys.stderr.write("Uploading content: ")
    sys.stderr.flush()
    if cmdline.type: #DTH
        ids = srv.getDeviceTypeIds(uuid)
        success = srv.uploadDeviceTypeItem(ids['versionid'], data, filename, path, kind)
    else:
        ids = srv.getSmartAppIds(uuid)
        success = srv.uploadSmartAppItem(ids['versionid'], data, filename, path, kind)
    if success:
        sys.stderr.write("OK\n")
    else:
        sys.stderr.write("Failed\n")
elif cmdline.action == "update":
    # Bundle UUID, item UUID, new content
    uuid = cmdline.options[0]
    item = cmdline.options[1]
    with open(cmdline.options[2], 'rb') as f:
        data = f.read()

    if cmdline.type: #DTH
        details = srv.getDeviceTypeDetails(uuid)
    else:
        details = srv.getSmartAppDetails(uuid)

    if item not in details["flat"]:
        print 'ERROR: Item is not in selected bundle'
        sys.exit(255)

    sys.stderr.write("Updating content: ")
    sys.stderr.flush()
    if cmdline.type: #DTH
        result = srv.updateDeviceTypeItem(details["details"], uuid, item, data)
    else:
        result = srv.updateSmartAppItem(details["details"], uuid, item, data)
    if "errors" in result and result["errors"]:
        print "Errors:"
        for e in result["errors"]:
            print "  " + e
    if "output" in result and result["output"]:
        print "Details:"
        for o in result["output"]:
            print "  " + o
    if not result["errors"] and not result["output"]:
        print "OK"
    else:
        sys.exit(1)
