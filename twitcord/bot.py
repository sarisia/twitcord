import asyncio
import inspect
import urllib
from datetime import datetime
from logging import getLogger

import discord
from aioauth_client import TwitterClient
from aiosqlite import connect as con

from .config import Config
from .subscriber import (FavoriteSubscriber, HomeTimelineSubscriber,
                         ListSubscriber)

log = getLogger(__name__)


class Twitcord(discord.Client):
    def __init__(self):
        self.config = Config()
        self.twitter = TwitterClient(
            consumer_key=self.config.twitter['consumerKey'],
            consumer_secret=self.config.twitter['consumerSecret'],
            oauth_token=self.config.twitter['token'],
            oauth_token_secret=self.config.twitter['tokenSecret']
        )
        self.db = "twitcord.db"
        self.loop = asyncio.get_event_loop()
        self.subs = []

        self._twitcord_ready = False

        super().__init__()
        
    def run(self):
        super().run(self.config.discord['token'])

    async def on_ready(self):
        if self._twitcord_ready:
            return

        asyncio.ensure_future(self.refresh(), loop=self.loop)
        self._twitcord_ready = True

    async def on_message(self, message):
        await self.wait_until_ready()

        # ignore bot itself
        if message.author.id == self.user.id:
            return

        # check command prefix
        if not message.content.startswith(self.config.command_prefix):
            return
        
        command = message.content
        arg = ""
        if len(message.content.split()) > 1:
            command, arg = command.split(maxsplit=1)
        
        command = command.strip(self.config.command_prefix)

        handler = getattr(self, "cmd_" + command, None)
        if not handler:
            return

        # construct args
        # use copy() to avoid `mappingproxy has no attribute 'pop'`
        handler_params = inspect.signature(handler).parameters.copy()
        kwargs = {}
        if handler_params.pop('text', None):
            kwargs['text'] = arg
        if handler_params.pop('channel', None):
            kwargs['channel'] = message.channel

        await handler(**kwargs)

    async def cmd_tweet(self, text):
        content = {
            'status': urllib.parse.quote(text)
        }

        await self._safe_twitter('POST', 'statuses/update', params=content)

    async def refresh(self):
        await asyncio.sleep(10)
        asyncio.ensure_future(self.refresh(), loop=self.loop)

        for subscriber in self.subs:
            log.debug(f'refreshing {subscriber.table_name}')
            log.debug(f'latest_id: {subscriber.latest_id}')
            tweets = await subscriber.refresh()
            channel = self.get_channel(subscriber.channel_id)
            if channel:
                await self._send_tweets(channel, tweets)
            else:
                log.error(f'Channel not found for id {subscriber.channel_id}')

    async def cmd_lists(self, channel):
        ret = await self._safe_twitter('GET', 'lists/list')
        print(ret)
        embed = discord.Embed(title='Lists')
        for item in ret:
            embed.add_field(name=item['full_name'].strip('/'), value=(item['description'] or 'No description'), inline=False)

        await channel.send(embed=embed)

    async def cmd_sub(self, channel, text):
        splitted = text.split('/')
        if len(splitted) == 2:
            params = {
                'owner_screen_name': splitted[0].strip('@'),
                'slug': splitted[1]
            }

            ret = await self._safe_twitter('GET', 'lists/show', params=params)
            if ret:
                self.subs.append(ListSubscriber(self._safe_twitter, channel.id, ret['id'], **params))
            else:
                log.error(f'List not found for {text}')
        else:
            log.error(f'Not subscribable: {text}')

    async def _safe_twitter(self, method, endpoint, **kwargs):
        ret = None
        try:
            ret = await self.twitter.request(method, endpoint + '.json', **kwargs)
        except Exception as e:
            # TODO: implement kindful errors
            log.error('Failed to communicate with Twitter API:')
            log.error(f'Request: {method}, {endpoint}')
            log.error(f'Status: {e}')

        return ret

    async def _send_tweets(self, channel: discord.ChannelType, tweets: list):
        for embed in [self._tweet_to_embed(tweet) for tweet in tweets]:
            await channel.send(embed=embed)

    def _tweet_to_embed(self, tweet: dict) -> discord.Embed:
        embed = discord.Embed()
        embed.set_author(name=tweet['user_name'], icon_url=tweet['user_icon'])
        embed.description = tweet['tweet']
        embed.timestamp = datetime.strptime(tweet['timestamp'], "%a %b %d %H:%M:%S %z %Y") # ctime

        return embed
