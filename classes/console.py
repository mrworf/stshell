import cmd
import re

class ConsoleAccess(cmd.Cmd):
    def updatePrompt(self):
        self.prompt = "%s/ > " % self.cwd

    def setConnection(self, conn):
        """ Assigns a STServer Connection to the console """
        self.conn = conn
        self.cwd = ""
        self.tree = {}
        # Prepopulate
        self.tree["/smartapps"] = {"name" : "/smartapps", "uuid" : None, "type" : None, "stale" : True}
        self.tree["/devices"] = {"name" : "/devices", "uuid" : None, "type" : None, "stale" : True}
        self.updatePrompt()

    def listBundle(self, node):
        pass

    def do_refresh(self, line):
        # format:
        # name = "complete/path/to/file.groovy" (also used as key)
        # uuid = "reference to actual file"
        # type = "sa, dth"
        # stale = True/False
        #
        # If stale is True, then this node should be reexplored
        pass

    def splitPath(self, path):
        p = re.compile('/+')
        return p.split(path)

    def do_cd(self, line):
        error = False
        parts = self.splitPath(line)
        cwd = self.cwd
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
                    if t.startswith(cwd + "/" + part):
                        cwd += "/" + part
                        found = True
                        break
                if not found:
                    error = True
                    break

        if error:
            print "Path not found: " + line
        else:
            self.cwd = cwd
            self.updatePrompt()


    def printFolderInfo(self, info):
        print "total %d" % len(info)
        for f in info:
            if f["dir"]:
                print "%s/" % f["name"]
            else:
                print "%s/" % f["name"]

    def do_ls(self, line):
        folderinfo = []

        # Iterate through tree, print all that matches
        paths = self.splitPath(self.cwd)
        for t in self.tree:
            if t.startswith(self.cwd + "/"):
                parts = self.splitPath(t)
                folderinfo.append(
                    {"name" : parts[len(paths)],
                    "dir" : len(parts) > len(paths)
                    }
                )

        self.printFolderInfo(folderinfo)


    def do_EOF(self, line):
        return True
