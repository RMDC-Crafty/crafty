import pprint
import os

class ServerProps:

    def __init__(self, filepath):
        self.filepath = filepath
        self.props = self._parse()

    def _parse(self):
        """Loads and parses the file speified in self.filepath"""
        with open(self.filepath) as fp:
            line = fp.readline()
            d = {}
            if os.path.exists(".header"):
                os.remove(".header")
            while line:
                if '#' != line[0]:
                    s = line
                    s1 = s[:s.find('=')]
                    if '\n' in s:
                        s2 = s[s.find('=')+1:s.find('\\')]
                    else:
                        s2 = s[s.find('=')+1:]
                    d[s1] = s2
                else:
                    with open(".header", "a+") as h:
                        h.write(line)
                line = fp.readline()
        return d

    def print(self):
        """Prints the properties dictionary (using pprint)"""
        pprint.pprint(self.props)
        
    def get(self):
        """Returns the properties dictionary"""
        return self.props

    def update(self, key, val):
        """Updates property in the properties dictionary [ update("pvp", "true") ] and returns boolean condition"""
        if key in self.props.keys():
            self.props[key] = val
            return True
        else:
            return False

    def save(self):
        """Writes to the new file"""
        with open(self.filepath, "a+") as f:
            f.truncate(0)
            with open(".header") as header:
                line = header.readline()
                while line:
                    f.write(line)
                    line = header.readline()
                header.close()
            for key, value in self.props.items():
                f.write(key + "=" + value + "\n")
        if os.path.exists(".header"):
                os.remove(".header")
            
