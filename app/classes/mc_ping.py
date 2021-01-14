import struct
import socket
import base64
import json
import sys
import logging.config

# credit to https://gist.github.com/Lonami - https://gist.github.com/Lonami/b09fc1abb471fd0b8b5483d54f737ea0
# slightly modified for Crafty

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, data):
        self.description = data.get('description')
        # print(self.description)
        if isinstance(self.description, dict):

            # cat server
            if "translate" in self.description:
                self.description = self.description['translate']

            # waterfall / bungee
            elif 'extra' in self.description:
                lines = []

                description = self.description
                if 'extra' in description.keys():
                    for e in description['extra']:
                        if "text" in e.keys():
                            lines.append(e['text'])

                total_text = " ".join(lines)
                self.description = total_text

            # normal MC
            else:
                self.description = self.description['text']

        self.icon = base64.b64decode(data.get('favicon', '')[22:])

        # if players key doesn't exists, we send a blank list object
        self.players = Players(data.get('players', [])).report()

        self.version = data['version']['name']
        self.protocol = data['version']['protocol']

    # def __str__(self):
    #    return 'Server(description={!r}, icon={!r}, version={!r}, '\
    #            'protocol={!r}, players={!r})'.format(
    #        self.description, bool(self.icon), self.version,
    #        self.protocol, self.players
    #    )


class Players(list):
    def __init__(self, data):
        super().__init__(Player(x) for x in data.get('sample', []))
        self.max = data['max']
        self.online = data['online']

    def report(self):
        players = []

        for x in self:
            players.append(str(x))

        r_data = {
            'online': self.online,
            'max': self.max,
            'players': players
        }

        return json.dumps(r_data)


class Player:
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']

    def __str__(self):
        return self.name


# For the rest of requests see wiki.vg/Protocol
def ping(ip, port=25565):
    def read_var_int():
        i = 0
        j = 0
        while True:
            k = sock.recv(1)
            if not k:
                return 0
            k = k[0]
            i |= (k & 0x7f) << (j * 7)
            j += 1
            if j > 5:
                raise ValueError('var_int too big')
            if not (k & 0x80):
                return i

    sock = socket.socket()
    try:
        sock.connect((ip, port))
    except:
        pass
        return False

    try:
        host = ip.encode('utf-8')
        data = b''  # wiki.vg/Server_List_Ping
        data += b'\x00'  # packet ID
        data += b'\x04'  # protocol variant
        data += struct.pack('>b', len(host)) + host
        data += struct.pack('>H', port)
        data += b'\x01'  # next state
        data = struct.pack('>b', len(data)) + data
        sock.sendall(data + b'\x01\x00')  # handshake + status ping
        length = read_var_int()  # full packet length
        if length < 10:
            if length < 0:
                return False
            else:
                return False

        sock.recv(1)  # packet type, 0 for pings
        length = read_var_int()  # string length
        data = b''
        while len(data) != length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                return False

            data += chunk
        logger.debug("Server reports this data on ping: {}".format(data))
        return Server(json.loads(data))
    finally:
        sock.close()
