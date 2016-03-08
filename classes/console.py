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
        self.tree = {}
        # Prepopulate
        self.tree["/smartapps"] = {"name" : "/smartapps", "uuid" : None, "parent" : None, "type" : None, "stale" : True}
        self.tree["/devices"] = {"name" : "/devices", "uuid" : None, "parent" : None, "type" : None, "stale" : True}
        self.updatePrompt()

    def listBundle(self, node):
        pass

    def do_refresh(self, line):
        """ Marks all directories as stale, forcing a reload from server """
        # format:
        # name = "complete/path/to/file.groovy" (also used as key)
        # uuid = "reference to actual file"
        # type = "sa, dth"
        # stale = True/False
        #
        # If stale is True, then this node should be reexplored
        pass

    def splitPath(self, path):
        path = path.split("/")
        new = []
        for p in path:
            if p:
                new.append(p)
        return new

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
            self.tree[filename] = {"name" : filename, "parent" : None, "uuid" : d["id"], "type" : None, "stale" : True}

    def loadItems(self, base, force=False):
        entry = self.tree[base]
        if base.startswith("/smartapps/"):
            kind = "sa"
            data = self.conn.getSmartAppDetails(entry["uuid"])
        elif base.startswith("/devices/"):
            kind = "dth"
            data = self.conn.getDeviceTypeDetails(entry["uuid"])
        for k,v in data["flat"].iteritems():
            filename = base + v
            self.tree[filename] = {"name" : filename, "parent" : entry["uuid"], "uuid" : k, "type" : kind, "stale" : True}

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

    def do_cd(self, line):
        """ Changes the current folder """
        cwd = self.resolvePath(line)
        if cwd is None:
            print "Path not found: " + line
        else:
            self.cwd = cwd
            self.updatePrompt()

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

    def do_ls(self, line):
        """ Shows the contents of current folder or the one provided as argument """
        folderinfo = []

        if line != "":
            cwd = self.resolvePath(line)
        else:
            cwd = self.cwd

        # See if we need to load something from the server
        self.loadFromServer(cwd)

        # Iterate through tree, print all that matches
        paths = self.splitPath(cwd)

        for t in self.tree:
            if t.startswith(cwd + "/"):
                parts = self.splitPath(t)
                folderinfo.append(
                    {"name" : parts[len(paths)],
                    "dir" : (len(parts)-1) > len(paths)
                    }
                )

        self.printFolderInfo(folderinfo)


    def do_EOF(self, line):
        """ Exits the console """
        return True
