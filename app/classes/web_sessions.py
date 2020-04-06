

class web_session():

    def __init__(self, username=None):
        self.data = {username: {}}

    def get_data(self, username, key):
        if username in self.data.keys():
            try:
                return self.data[username][key]
            except:
                pass

        return False

    def set_data(self, username, key, value):
        self.data[username][key] = value

    def del_data(self, username, key):
        try:
            del self.data[username][key]
        except:
            pass
