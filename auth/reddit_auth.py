import praw
import yaml

def load_creds(file):
    with open(file) as file:
        auth = yaml.load(file, Loader=yaml.FullLoader)

    return praw.Reddit(
        client_id=auth['client_id'],
        client_secret=auth['client_secret'],
        user_agent=auth['user_agent'],
        password = auth['password'],
        username = auth['username']
    )
def load_config(file):
    with open(file) as file:
        return yaml.load(file, Loader=yaml.FullLoader)

def load_keywords(file):
    with open(file, 'r',) as f:
        return yaml.load(f, Loader=yaml.FullLoader)
