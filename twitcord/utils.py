import discord
from datetime import datetime


def tweet_factory(cursor, row):
    """
    Passed to sqlite3 connection as row_factory. 
    """

    ret = {}
    for index, key in enumerate(cursor.description):
        ret[key[0]] = row[index]
    
    return ret

def twitter_url(user=None, status=None):
    tail = ''
    if user:
        if status:
            tail = f'{user}/status/{str(status)}'
        else:
            tail = user
    
    return 'https://twitter.com/' + tail

def tweet_to_embed(tweet):
    embed = discord.Embed()
    embed.set_author(name=tweet['user_name'], icon_url=tweet['user_icon'], url=twitter_url(user=tweet['user_screen_name'], status=tweet['id']))
    embed.description = tweet['tweet']
    embed.timestamp = datetime.strptime(tweet['timestamp'], "%a %b %d %H:%M:%S %z %Y") # ctime

    return embed
