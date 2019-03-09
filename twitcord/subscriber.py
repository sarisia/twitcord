from logging import getLogger

from .database import TableManager

log = getLogger(__name__)

# TODO: serializer / deserializer
# TODO: don't use separeted table (use single tweet store)

class Subscriber():
    endpoint = ''
    table_name = ''

    def __init__(self, twitter, channel_id):
        self.twitter = twitter
        self.channel_id = channel_id

        self.endpoint = self.endpoint
        self.table = TableManager(self.table_name)
        self.latest_id = 0

    
    @staticmethod
    def format_tweet(content):
        ret = []

        for item in content:
            ret.append({
                'id': item['id'],
                'user_name': item['user']['name'],
                'user_icon': item['user']['profile_image_url_https'],
                'tweet': item['text'],
                'timestamp': item['created_at']
            })

        return ret

    async def refresh(self):
        ret = None
        
        to_db = self.format_tweet(await self._fetch())
        await self.table.update(to_db)

        if self.latest_id:
            ret = await self.table.diffs(self.latest_id)
        elif to_db:
            to_db.sort(key=lambda item: item['id'])
            self.latest_id = to_db[-1]['id']
            log.debug(f'set latest_id to {self.latest_id}')

        if ret:
            self.latest_id = ret[-1]['id']
        return ret or ()

    async def _fetch(self):
        return await self.twitter('GET', self.endpoint)

class HomeTimelineSubscriber(Subscriber):
    endpoint = 'statuses/home_timeline'
    table_name = 'home_timeline'

class ListSubscriber(Subscriber):
    endpoint = 'lists/statuses'
    
    def __init__(self, twitter, channel, list_id, owner_screen_name, slug):
        self.table_name = f'{owner_screen_name}_{slug}'
        self.list_id = list_id
        
        super().__init__(twitter, channel)

    async def _fetch(self):
        return await self.twitter('GET', self.endpoint, params={'list_id': self.list_id})

class FavoriteSubscriber(Subscriber):
    endpoint = 'favorites/list'
    table_name = 'favorites'

    async def _fetch(self):
        return await self.twitter('GET', self.endpoint, params={'count': 50})

