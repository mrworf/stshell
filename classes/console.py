import cmd
import re
import sys
import os
import glob

class ConsoleAccess(cmd.Cmd):
    def updatePrompt(self):
        self.prompt = "%s/ > " % self.cwd

    def setConnection(self, conn):
        """ Assigns a STServer Connection to the console """
        self.conn = conn
        self.cwd = ""
        # Prepopulate
        self.tree = {}
        self.tree["/smartapps"] = {"name" : "/smartapps", "dir" : True, "uuid" : None, "parent" : None, "type" : None, "stale" : True}
        self.tree["/devices"] = {"name" : "/devices", "dir" : True, "uuid" : None, "parent" : None, "type" : None, "stale" : True}
        self.updatePrompt()

    def listBundle(self, node):
        pass

    def do_refresh(self, line):
        """ Marks all directories as stale, forcing a reload from server """
        # Prepopulate
        print "Please wait, reloading..."
        self.tree = {}
        self.tree["/smartapps"] = {"name" : "/smartapps", "dir" : True, "uuid" : None, "parent" : None, "type" : None, "stale" : True}
        self.tree["/devices"] = {"name" : "/devices", "dir" : True, "uuid" : None, "parent" : None, "type" : None, "stale" : True}
        self.do_cd(self.cwd)

    def splitPath(self, path):
        """ Splits the path into an array of parts """
        path = path.split("/")
        new = []
        for p in path:
            if p:
                new.append(p)
        return new

    def getParent(self, path):
        """ Removes one section of the provided path """
        path = self.splitPath(path)
        if len(path) < 2:
            return None
        result = ""
        for i in range(0, len(path)-1):
            result += "/" + path[i]
        return result

    def generateTrail(self, filename, kind=None, parent=None, uuid=None):
        """ Fills in the gaps in the directory structure """
        parts = self.splitPath(filename)
        cd = ""
        for p in parts:
            cd += "/" + p
            if cd not in self.tree:
                self.tree[cd] = {"name" : cd, "uuid" : uuid, "parent" : parent, "type" : kind, "stale" : False, "dir" : True}

    def loadList(self, base, force=False):
        if not self.tree[base]["stale"]:
            return

        if base == "/smartapps":
            kind = 'sa'
            data = self.conn.listSmartApps()
        elif base == "/devices":
            kind = 'dth'
            data = self.conn.listDeviceTypes()

        self.tree[base]["stale"] = False
        for d in data.values():
            filename = base + "/" + d["namespace"] + "/" + d["name"]
            self.tree[filename] = {"name" : filename, "dir" : True, "parent" : d["id"], "uuid" : None, "type" : kind, "stale" : True}
            self.generateTrail(filename, kind=kind)

    def loadItems(self, base, force=False):
        entry = self.tree[base]
        if entry["stale"]:
            if base.startswith("/smartapps/"):
                kind = "sa"
                data = self.conn.getSmartAppDetails(entry["parent"])
            elif base.startswith("/devices/"):
                kind = "dth"
                data = self.conn.getDeviceTypeDetails(entry["parent"])
            for k,v in data["flat"].iteritems():
                filename = base + v
                self.tree[filename] = {"name" : filename, "dir" : False, "parent" : entry["parent"], "uuid" : k, "type" : kind, "stale" : False}
                self.generateTrail(filename, kind, entry["parent"])
            # Also add static folders
            for k in self.conn.UPLOAD_TYPE.values():
                filename = base + "/" + k
                self.generateTrail(filename, kind, entry["parent"])
            entry["stale"] = False # Avoid loading this again

        #print repr(data)

    def loadFromServer(self, base, force=False):
        if base in self.tree:
            if base == "/smartapps" or base == "/devices":
                self.loadList(base, force)
            elif base in self.tree:
                self.loadItems(base, force)
            else:
                print("ERR: Not supported yet (%s)" % base)

    def resolvePath(self, line):
        error = False
        parts = self.splitPath(line)
        cwd = self.cwd
        progress = False
        if line[0] == "/":
            cwd = ""
        for part in parts:
            paths = self.splitPath(cwd)
            if part == ".." and len(paths):
                cwd = ""
                for i in range(0, len(paths)-1):
                    cwd += "/" + paths[i]
            elif part == "..":
                error = True
            else:
                found = False
                for t in self.tree:
                    search = cwd + "/" + part
                    if t.startswith(search + "/") or t == search:
                        cwd += "/" + part
                        if not self.tree[cwd]["dir"]:
                            error = True
                            break
                        found = True
                        break
                if not found:
                    error = True
                    break
                elif cwd in self.tree and self.tree[cwd]["stale"]:
                    self.loadFromServer(cwd)
        if error:
            return None
        else:
            return cwd

    def partialPath(self, line):
        error = False
        parts = self.splitPath(line)
        cwd = self.cwd
        progress = False
        results = []
        if line[0] == "/":
            cwd = ""
        for part in parts:
            paths = self.splitPath(cwd)
            if part == ".." and len(paths):
                cwd = ""
                for i in range(0, len(paths)-1):
                    cwd += "/" + paths[i]
            elif part == "..":
                break
            else:
                found = False
                for t in self.tree:
                    search = cwd + "/" + part
                    if t.startswith(search):
                        results.append(t)
                        found = True
                if found and cwd in self.tree and self.tree[cwd]["stale"]:
                    self.loadFromServer(cwd)

        return results

    def printFolderInfo(self, info):
        shown = {}
        for f in info:
            if f["name"] in shown:
                continue

            if f["dir"]:
                shown[f["name"]] = "%s/" % f["name"]
            else:
                shown[f["name"]] = "%s" % f["name"]
        print "total %d" % len(shown)
        for f in shown.values():
            print f

    def emptyline(self):
        pass

    def downloadFile(self, item, dstfile):
        """ Downloads a specific file to dstfile, does NOT create folder structure! """
        sys.stdout.write('Downloading "%s" ... ' % dstfile)
        sys.stdout.flush()

        if item["type"] == 'sa':
            contents = self.conn.getSmartAppDetails(item["parent"])
            data = self.conn.downloadSmartAppItem(item["parent"], contents["details"], item["uuid"])
        elif item["type"] == 'dth':
            contents = self.conn.getDeviceTypeDetails(item["parent"])
            data = self.conn.downloadDeviceTypeItem(item["parent"], contents["details"], item["uuid"])

        with open(dstfile, "wb") as f:
            f.write(data["data"])

        print "Done (%d bytes)" % len(data["data"])

    def updateFile(self, item, filename):
        sys.stdout.write('Updating "%s" ... ' % filename)
        sys.stdout.flush()

        with open(filename, 'rb') as f:
            data = f.read()

        result = None
        if item["type"] == 'sa':
            contents = self.conn.getSmartAppDetails(item["parent"])
            result = self.conn.updateSmartAppItem(contents["details"], item["parent"], item["uuid"], data)
        elif item["type"] == 'dth':
            contents = self.conn.getDeviceTypeDetails(item["parent"])
            result = self.conn.updateDeviceTypeItem(contents["details"], item["parent"], item["uuid"], data)
        if result and not result["errors"] and not result["output"]:
            print "OK"
        else:
            print "Failed"
        return result

    def uploadFile(self, item, filename, kind, path):
        """ Uploads a new file to the server """
        sys.stdout.write('Uploading "%s" ... ' % filename)
        sys.stdout.flush()

        with open(filename, 'rb') as f:
            data = f.read()

        result = None
        if item["type"] == 'sa':
            ids = self.conn.getSmartAppIds(item["parent"])
            success = self.conn.uploadSmartAppItem(ids['versionid'], data, filename, path, kind)
        elif item["type"] == 'dth':
            ids = self.conn.getDeviceTypeIds(item["parent"])
            success = self.conn.uploadDeviceTypeItem(ids['versionid'], data, filename, path, kind)
        if success:
            print "OK"
        else:
            print "Failed"
        return success

    def deleteFile(self, item):
        sys.stdout.write('Deleting file "%s" ... ' % os.path.basename(item['name']))
        sys.stdout.flush()
        if item["type"] == 'sa':
            self.conn.deleteSmartAppItem(item['parent'], item['uuid'])
        elif item['type'] == 'dth':
            self.conn.deleteDeviceTypeItem(item['parent'], item['uuid'])
        print "OK"

    def deleteModule(self, item):
        sys.stdout.write('Deleting module "%s" ... ' % os.path.basename(item['name']))
        sys.stdout.flush()
        if item["type"] == 'sa':
            self.conn.deleteSmartApp(item['parent'])
        elif item['type'] == 'dth':
            self.conn.deleteDeviceType(item['parent'])
        print "OK"

    def createModule(self, kind, filename):
        t = 'SmartApp'
        if kind == 'dth':
            t = 'DeviceTypeHandler'
        sys.stdout.write('Creating %s from "%s" ... ' % (t, os.path.basename(filename)))
        sys.stdout.flush()
        with open(filename, "rb") as f:
            data = f.read()
        result = None
        if kind == 'sa':
            result = self.conn.createSmartApp(data)
        elif kind == 'dth':
            result = self.conn.createDeviceType(data)
        if result:
            print "OK"
        else:
            print "Failed"
        return result

    def publishModule(self, module):
        sys.stdout.write('Publishing "%s" ... ' % (os.path.basename(module["name"])))
        sys.stdout.flush()
        result = None
        if module["type"] == 'sa':
            result = self.conn.publishSmartApp(module["parent"])
        elif module["type"] == 'dth':
            result = self.conn.publishDeviceType(module["parent"])
        if result:
            print "OK"
        else:
            print "Failed"
        return result

    def do_pwd(self, line):
        """ Shows current folder """
        print('Current folder: "%s/" on %s' % (self.cwd, self.conn.URL_BASE))

    def do_cd(self, line):
        """ Changes the current folder """
        if line == "":
            self.do_pwd(line)
            return

        cwd = self.resolvePath(line)
        if cwd is None:
            print 'Path not found: "%s"' % line
        else:
            self.cwd = cwd
            self.updatePrompt()

    def do_ls(self, line):
        """ Shows the contents of current folder or the one provided as argument """
        folderinfo = []

        if line != "":
            cwd = self.resolvePath(line)
        else:
            cwd = self.cwd

        if cwd is None:
            print 'Path not found: "%s"' % line
            return

        # See if we need to load something from the server
        self.loadFromServer(cwd)

        # Iterate through tree, print all that matches
        paths = self.splitPath(cwd)

        for t in self.tree:
            if t.startswith(cwd + "/"):
                parts = self.splitPath(t)
                filename = parts[len(paths)]
                info = {"name" : filename,
                        "dir" : self.tree[cwd + "/" + filename]["dir"]
                        }
                folderinfo.append(info)

        self.printFolderInfo(folderinfo)

    def do_dir(self, line):
        """ Alias for ls """
        return self.do_ls(line)

    def do_debug(self, line):
        print "DEBUG INFO - TREE:"
        for v in self.tree.values():
            if line == "" or line in repr(v):
                print repr(v)

    def do_get(self, line):
        """ Downloads a file or directory """
        if line[0] == "/":
            filename = line
        else:
            filename = self.cwd + "/" + line

        # Make sure we load anything we need to do this
        path = os.path.dirname(filename)
        if path != self.cwd:
            print 'Resolving "%s"' % path
            self.resolvePath(path)

        if filename not in self.tree:
            print 'ERROR: No such file "%s"' % filename
            return
        item = self.tree[filename]
        if item["dir"]:
            print 'Downloading directory "%s"' % line
            # Time to traverse our tree and show what we WOULD be downloading...
            print "Would download:"
            size = 0
            processed = []
            while len(self.tree) != size:
                size = len(self.tree)
                for i in self.tree:
                    if i in processed:
                        continue

                    if i.startswith(item["name"]):
                        self.resolvePath(i)
                        # Restart if tree changes
                        if len(self.tree) != size:
                            break
                        dstfile = i[len(filename)+1:]
                        if self.tree[i]["dir"]:
                            try:
                                os.makedirs(dstfile)
                            except:
                                pass
                        else:
                            try:
                                d = os.path.dirname(dstfile)
                                os.makedirs(d)
                            except:
                                pass
                            self.downloadFile(self.tree[i], dstfile)
                        processed.append(i)
            return
        else:
            dstfile = os.path.basename(filename)
            self.downloadFile(item, dstfile)

    def do_lcd(self, line):
        """ Change current local directory """
        if line != "":
            try:
                os.chdir(line)
            except:
                print "ERROR: Invalid directory"
        print 'Current local directory: "%s"' % os.getcwd()

    def do_lmkdir(self, line):
        """ Creates a directory locally """
        if line == "":
            print "ERROR: Need directory name"
            return
        try:
            os.mkdir(line)
        except:
            print "ERROR: Couldn't create \"%s\"" % line

    def do_lls(self, line):
        """ List the files in the current local directory """
        if line == "":
            cwd = os.getcwd()
        elif line[0] == '/':
            cwd = line
        else:
            cwd = os.getcwd() + '/' + line

        try:
            data = os.listdir(cwd)
        except:
            print "ERROR: Invalid directory"
            return

        folderinfo = []
        for f in data:
            info = {"name" : f,
                    "dir" : os.path.isdir(cwd + "/" + f)
                    }
            folderinfo.append(info)

        self.printFolderInfo(folderinfo)

    def do_put(self, line):
        """ Upload a file to the current directory, overwrite if already exists """

        # Make sure the file exists
        dstfile = None
        srcfile = None
        if os.path.exists(line) and os.path.isfile(line):
            dstfile = os.path.basename(line)
            srcfile = line
        else:
            print "ERROR: \"%s\" does not exist" % line
            return False

        # Find out if the user is allowed to upload here
        if self.cwd != "":
            dst = self.tree[self.cwd]
        else:
            dst = None

        # The simple case...
        if dst is None or dst["parent"] == None:
            print "ERROR: You don't have permission to upload here"
            return False

        # Get the base directory and details
        cwd = self.cwd
        while self.tree[cwd]["parent"]:
            prev = cwd
            cwd = self.getParent(cwd)
        base = self.tree[prev]
        dstpath = (self.cwd + '/')[len(base["name"])+1:]

        # We should NOT allow upload in the base directory of a DTH/SA
        # unless it overwrites the existing groovy file
        if (self.cwd + '/' + dstfile) not in self.tree:
            if dstpath == "":
                print "ERROR: You can only upload the original groovy file here"
            else:
                # TIme to figure out what type it is
                parts = self.splitPath(dstpath)
                kind = None
                for k,v in self.conn.UPLOAD_TYPE.iteritems():
                    if v == parts[0]:
                        kind = k
                        break
                if not kind:
                    print "ERROR: You don't have permission to upload here"
                    return False
                path = ""
                for p in parts[1:]:
                    path += '/' + p
                if path != "":
                    path = path[1:]
                result = self.uploadFile(base, srcfile, kind, path)
                if result:
                    # We need to refresh this branch
                    base["stale"] = True
                    self.resolvePath(self.cwd)
        else:
            dst = self.tree[(self.cwd + '/' + dstfile)]
            result = self.updateFile(dst, srcfile)
            if result is None:
                print "Internal error"
            else:
                if "errors" in result and result["errors"]:
                    print "Errors:"
                    for e in result["errors"]:
                        print "  " + e
                if "output" in result and result["output"]:
                    print "Details:"
                    for o in result["output"]:
                        print "  " + o
        return True

    def do_mput(self, line):
        if line == "":
            return
        files = glob.glob(line)
        if len(files) == 0:
            return
        for f in files:
            if not self.do_put(f):
                break

    def do_rm(self, line):
        """ Deletes a file """
        if line == "":
            return
        filename = self.cwd + '/' + line
        if filename not in self.tree:
            print "ERROR: No such file \"%s\"" % filename
            return
        if self.tree[filename]["dir"]:
            print "ERROR: Can't delete directory"
            return

        cwd = self.cwd
        while self.tree[cwd]["parent"]:
            prev = cwd
            cwd = self.getParent(cwd)
        base = self.tree[prev]
        dstpath = (self.cwd + '/')[len(base["name"])+1:]
        if dstpath == "":
            print "ERROR: This would delete the entire module, aborting"
            return
        self.deleteFile(self.tree[filename])
        self.tree.pop(filename, None)

    def do_rmmod(self, line):
        """ Deletes an entire smartapp or devicetype handler, use it on the base folder """
        if line == "":
            return
        filename = self.cwd + '/' + line
        if filename not in self.tree:
            print "ERROR: No such module \"%s\"" % filename
            return
        if self.tree[filename]['parent'] is None:
            print "ERROR: Not a module \"%s\"" % filename
            return
        parent = self.getParent(filename)
        if self.tree[parent]['parent'] is not None:
            print "ERROR: Not a module \"%s\"" % filename
            return
        sys.stderr.write('WARNING! This will delete the module "%s", are you sure? (yes/NO) ' % filename)
        sys.stderr.flush()
        choice = sys.stdin.readline().strip().lower()
        if choice == "yes":
            self.deleteModule(self.tree[filename])
            # Remove ALL references
            lst = []
            for k in self.tree:
                if k.startswith(filename + '/') or k == filename:
                    lst.append(k)
            for l in lst:
                self.tree.pop(l)
        else:
            print "Operation aborted"

    def do_create(self, line):
        """ Creates a new SmartApp or DeviceTypeHandler """
        if line == "" or not os.path.exists(line):
            print "ERROR: You must provide groovy file to create new module"
            return
        filename = line
        kind = None
        if self.cwd == '/smartapps':
            kind = 'sa'
        elif self.cwd == '/devices':
            kind = 'dth'
        if kind is None:
            print "ERROR: You cannot create a new module here"
            return
        result = self.createModule(kind, filename)
        if result:
            # We need to invalidate the cache so user sees the new module
            if kind == 'sa':
                self.tree['/smartapps']['stale'] = True
            else:
                self.tree['/devices']['stale'] = True
            self.resolvePath(self.cwd)

    def do_publish(self, line):
        """ Publishes changes to a SmartApp or DeviceTypeHandler """
        if line == "":
            print "ERROR: You must provide module name"
            return
        if line == '.':
            # Trick, if you stand inside the module, this will publish it
            module = self.cwd
        else:
            module = self.cwd + '/' + line

        if module not in self.tree or self.tree[module]["parent"] is None:
            print "ERROR: Cannot find module \"%s\"" % line
            return

        while self.tree[module]["parent"]:
            prev = module
            module = self.getParent(module)
        base = self.tree[prev]
        self.publishModule(base)

    def do_rmdir(self, line):
        """ Normally would delete directory, but this is not needed since it's handled automatically """
        print "INFO: This command has no function since server deals internally with empty directories"
        return

    def do_mkdir(self, line):
        """ Create a directory. Please note that if you never place any files in this directory, it will disappear """
        if line == "":
            print "ERROR: Need name for new directory"
            return
        if '/' in line or '.' in line:
            print 'ERROR: Cannot create directory outside of current'
            return
        if self.cwd != "":
            dst = self.tree[self.cwd]
        else:
            dst = None

        # The simple case...
        if dst is None or dst["parent"] == None:
            print "ERROR: You don't have permission to create a directory here"
            return

        # Get the base directory and details
        cwd = self.cwd
        while self.tree[cwd]["parent"]:
            prev = cwd
            cwd = self.getParent(cwd)
        base = self.tree[prev]
        dstpath = (self.cwd + '/')[len(base["name"])+1:]
        if dstpath == '':
            print "ERROR: You don't have permission to create a directory here"
            return

        filename = self.cwd + '/' + line
        self.tree[filename] = {"name" : filename, "dir" : True, "parent" : base["parent"], "uuid" : None, "type" : base['type'], "stale" : False}
        return

    def do_EOF(self, line):
        """ Exits the console """
        return True
