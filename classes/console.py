import cmd
import re
import sys

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
        path = path.split("/")
        new = []
        for p in path:
            if p:
                new.append(p)
        return new

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
            data = self.conn.listSmartApps()
        elif base == "/devices":
            data = self.conn.listDeviceTypes()

        self.tree[base]["stale"] = False
        for d in data.values():
            filename = base + "/" + d["namespace"] + "/" + d["name"]
            self.tree[filename] = {"name" : filename, "dir" : True, "parent" : d["id"], "uuid" : None, "type" : None, "stale" : True}
            self.generateTrail(filename)

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

    def do_pwd(self, line):
        """ Shows current folder """
        print("Current folder: "%s/" on %s" % (self.cwd, self.conn.URL_BASE))

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

    def disabled_complete_cd(self, text, line, begidx, endidx):
        # Text contains whatever partial info the user has tapped
        print 'DEBUG: Text = "%s", Line = "%s", begidx = "%s", endidx = "%s"' % (text, line, begidx, endidx)

        # Scan tree for a matching item
        if text != "":
            cwd = self.resolvePath(text)
        else:
            cwd = self.cwd

        if cwd is None:
            cwd = self.cwd + "/" + text

        print "CWD = " + cwd

        self.loadFromServer(cwd)

        # Iterate through tree, print all that matches
        paths = self.splitPath(cwd)
        result = []
        #print "Looking for " + cwd
        for t in self.tree:
            if t.startswith(cwd) and self.tree[t]["uuid"] == None:
                parts = self.splitPath(t)
                result.append(parts[len(parts)-1] + "/")
        return result

    def complete_ls(self, text, line, begidx, endidx):
        pass

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
        """ Downloads a file, does not yet support paths """
        filename = self.cwd + "/" + line
        if filename not in self.tree:
            print 'ERROR: No such file "%s"' % filename
            return
        item = self.tree[filename]
        if item["parent"] is None:
            print 'ERROR: Cannot download "%s", it\'s a directory'
            return

        dstfile = os.path.basename(filename)
        sys.stdout.write('Downloading "%s" ... ' % dstfile)
        sys.stdout.flush()
        if item["type"] == 'sa':
            data = self.conn.downloadSmartAppItem(item["parent"], )


    def do_EOF(self, line):
        """ Exits the console """
        return True
