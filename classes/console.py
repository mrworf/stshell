import cmd

class ConsoleAccess(cmd.Cmd):
    def setConnection(self, conn):
        """ Assigns a STServer Connection to the console """
        self.conn = conn

    def do_EOF(self, line):
        return True
