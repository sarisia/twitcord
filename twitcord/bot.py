import asyncio
import inspect
import urllib
from datetime import datetime
from logging import getLogger

import discord

from .config import Config
from .subscriber import (FavoriteSubscriber, HomeTimelineSubscriber,
                         ListSubscriber, UserTimelineSubscriber)
from .twitter import TwitterWrapper
from .utils import tweet_to_embed

log = getLogger(__name__)


class Twitcord(discord.Client):
    def __init__(self):
        self.config = Config()
        self.twitter = TwitterWrapper(
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

        asyncio.ensure_future(self.refresh_all(), loop=self.loop)
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
        # use copy() to convert mappingproxy to list
        handler_params = inspect.signature(handler).parameters.copy()
        kwargs = {}
        if handler_params.pop('text', None):
            kwargs['text'] = arg
        if handler_params.pop('channel', None):
            kwargs['channel'] = message.channel

        await handler(**kwargs)

    async def refresh_all(self):
        await asyncio.sleep(10)
        asyncio.ensure_future(self.refresh_all(), loop=self.loop)

        if self.subs:
            log.debug(f'start refresh {len(self.subs)} subscribers')
            await asyncio.wait([self._refresh_subscriber(sub) for sub in self.subs])

    async def _refresh_subscriber(self, subscriber):
        log.debug(f'refreshing {subscriber.table_name}: {subscriber.latest_id}')
        tweets = await subscriber.refresh()
        channel = self.get_channel(subscriber.channel_id)
        if channel:
            await self._send_tweets(channel, tweets)
        else:
            log.error(f'Channel not found for id {subscriber.channel_id}')

    async def cmd_tweet(self, text):
        content = { 'status': urllib.parse.quote(text) }
        await self.twitter.post('statuses/update', params=content)

    async def cmd_lists(self, channel):
        ret = await self.twitter.get('lists/list')
        print(ret)
        embed = discord.Embed(title='Lists')
        for item in ret:
            embed.add_field(name=item['full_name'].strip('/'), value=(item['description'] or 'No description'), inline=False)

        await channel.send(embed=embed)

    async def cmd_sub(self, channel, text):
        splitted = text.split('/')
        if len(splitted) == 1:
            if splitted[0] == 'home':
                self.subs.append(HomeTimelineSubscriber(self.twitter, channel.id))
                log.info('Subscribed home timeline')
            else:
                ret = await self.twitter.get('users/show', params={'screen_name': splitted[0]})
                if ret:
                    self.subs.append(UserTimelineSubscriber(self.twitter, channel.id, ret['id']))
                    log.info(f'Subscribed user {splitted[0]} ({ret["id"]})')
                else:
                    log.info(f'User not found: {splitted[0]}')
        elif len(splitted) == 2:
            if splitted[1] in ['favs', 'favorites']:
                ret = await self.twitter.get('users/show', params={'screen_name': splitted[0]})
                if ret:
                    self.subs.append(FavoriteSubscriber(self.twitter, channel.id, ret['id']))
                    log.info(f'Subscribed favorite {splitted[0]} ({ret["id"]})')
                else:
                    log.info(f'User not found: {splitted[0]}')
            else:                
                params = {
                    'owner_screen_name': splitted[0].strip('@'),
                    'slug': splitted[1]
                }

                ret = await self.twitter.get('lists/show', params=params)
                if ret:
                    self.subs.append(ListSubscriber(self.twitter, channel.id, ret['id']))
                else:
                    log.error(f'List not found for {text}')
        else:
            log.error(f'Not subscribable: {text}')

    async def _send_tweets(self, channel: discord.ChannelType, tweets: list):
        for tweet in tweets:
            log.debug(f"dispatching: {channel}: {tweet['id']}")
            await channel.send(embed=tweet_to_embed(tweet))
