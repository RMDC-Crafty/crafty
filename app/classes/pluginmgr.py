import requests
from datetime import datetime

from app.classes.helpers import helper

class PluginAPI():
    
    def __init__(self, api_url="https://api.spiget.org/v2/", user_agent_prefix="CraftyController"):
        # Set our vars
        self.api_url = api_url
        self.user_agent = "{}{}".format(user_agent_prefix, 
                                        helper.get_version())
        self.headers = {"User-Agent": self.user_agent}
    
    def search(self, query):
        """Search plugin API for a specific plugin. Sanitize the input!!"""
        # Format the URL
        url = "{}search/resources/{}".format(self.api_url, query)
        plugins = []
        # Request the resource
        r = requests.get(url, headers=self.headers)
        # Iterate through plugins
        for p in r.json():
            plugins.append({
                "name": p['name'],
                "rating": p['rating']['average'],
                "download_count": p['downloads'],
                "icon_url": p['icon']['url'],
                "file_url": p['file']['url'],
                "desc": p['tag'],
                "author": self.get_author(p['author']['id']),
                # Convert to python timestamp
                "updated_last": datetime.fromtimestamp(p['updateDate']),
                "server_versions": p['testedVersions']
            })
        return plugins
    
    def get_author(self, id):
        """Get author name from provided ID"""
        # Format the url
        url = "{}authors/{}".format(self.api_url, id)
        # Request the resource
        r = requests.get(url, headers=self.headers)
        # Get name
        try:
            name = r.json()['name']
        except:
            name = "Unknown"
        return name
    
plugins = PluginAPI()
        