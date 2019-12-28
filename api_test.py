import requests

API_TOKEN = "XDUsNc4ZVcrqiojnNMsbNuI1Mn5J9H6gU_dDUOQSs9g"
URL = "https://127.0.0.1:8000/api/v1/stats"
url2 = "HTTPS://127.0.0.1:8000/api/v1/server/send_command"
url3 = 'HTTPS://127.0.0.1:8000/api/v1/crafty/get_logs'
ONLINE_URL = "https://127.0.0.1:8000/api/v1/online"

#print(requests.post(URL, params={'token': API_TOKEN}, data={'command':'say Hello'}, verify=False).text)

print(requests.post(url3, params={'token': API_TOKEN, 'name':'ftp'}, verify=False).text)