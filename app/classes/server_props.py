import pprint
import os

class ServerProps:

    #Initialises the Class Variables
    def __init__(self, filepath):
        self.filepath = filepath
        self.props = self._parse()

    #Parses the file on self.filepath
    def _parse(self):
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

    #Prints the properties dictionary
    def print(self):
        pprint.pprint(self.props)
        
    #Returns the properties dictionary
    def get(self):
        return self.props

    #Updates property in the properties dictionary [ update("pvp", "true") ]
    def update(self, prop, val):
        if prop in self.props.keys():
            self.props[prop] = val
        else:
            print("Property not found.\n")

    #Writes the new file
    def save(self):
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
            
