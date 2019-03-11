from logging import getLogger

from .database import TableManager

log = getLogger(__name__)

# TODO: serializer / deserializer
# TODO: don't use separeted table (use single tweet store)

class Subscriber():
    endpoint = ''
    table_name = ''
    params = {}

    def __init__(self, twitter, channel_id):
        self.twitter = twitter
        self.channel_id = channel_id

        self.endpoint = self.endpoint
        self.table = TableManager(self.table_name)
        self.params = self.params
        self.latest_id = 0

    
    @staticmethod
    def format_tweet(content):
        ret = []

        for item in content:
            ret.append({
                'id': item['id'],
                'user_name': item['user']['name'],
                'user_screen_name':item['user']['screen_name'],
                'user_icon': item['user']['profile_image_url_https'],
                'tweet': item['full_text'],
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
            ret = to_db[-5:]
        
        if ret:
            self.latest_id = ret[-1]['id']

        return ret or []

    async def _fetch(self):
        self.params.update({'tweet_mode': 'extended'})
        return await self.twitter.get(self.endpoint, params=self.params)

class HomeTimelineSubscriber(Subscriber):
    endpoint = 'statuses/home_timeline'
    table_name = 'home_timeline'

class UserTimelineSubscriber(Subscriber):
    endpoint = 'statuses/user_timeline'

    def __init__(self, twitter, channel, user_screen_name):
        self.table_name = user_screen_name
        self.user = user_screen_name

        super().__init__(twitter, channel)

        self.params['screen_name'] = self.user

class ListSubscriber(Subscriber):
    endpoint = 'lists/statuses'
    
    def __init__(self, twitter, channel, list_id, owner_screen_name, slug):
        self.table_name = f'{owner_screen_name}_{slug}'
        self.list_id = list_id
        
        super().__init__(twitter, channel)

        self.params['list_id'] = self.list_id

class FavoriteSubscriber(Subscriber):
    endpoint = 'favorites/list'
    params = {
        'count': 50
    }

    def __init__(self, twitter, channel, user_screen_name):
        self.table_name = f'{user_screen_name}_favorites'
        self.user = user_screen_name

        super().__init__(twitter, channel)

        self.params['screen_name'] = self.user
