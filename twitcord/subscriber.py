from enum import IntEnum, auto
from logging import getLogger

from .database import TableManager

log = getLogger(__name__)

# TODO: lock
# TODO: don't use separeted table (use single tweet store)

class SubsType(IntEnum):
    Subscriber = auto()
    HomeTimeline = auto()
    UserTimeline = auto()
    List = auto()
    Favorite = auto()

class Subscriber():
    subtype = SubsType.Subscriber
    endpoint = ''
    table_name = ''
    params = {}

    def __init__(self, twitter, channel_id, *, data=None):
        self.twitter = twitter
        self.channel_id = channel_id
        self.latest_id = 0
        self.params = self.params.copy()

        if data:
            self.table_name = data['table_name']
            self.latest_id = data['latest_id']
            self.params = data['params']

        self.table = TableManager(self.table_name)
        self.params['tweet_mode'] = 'extended'

    def serialize(self):
        return {
            'subtype': int(self.subtype),
            'data': {
                'table_name': self.table_name,
                'channel_id': self.channel_id,
                'latest_id': self.latest_id,
                'params': self.params
            }
        }

    @classmethod
    def deserialize(cls, twitter, data):
        return cls(twitter, data['channel_id'], data=data)

    def format_tweet(self, content):
        ret = []

        for item in content:
            ret.append({
                'id': item['id'],
                'user_id': item['user']['id'],
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
            log.debug(f'{self.table_name}: diffs length {len(ret)}')
        elif to_db:
            to_db.sort(key=lambda item: item['id'])
            ret = to_db[-5:]
        
        if ret:
            log.debug(f'{self.table_name}: latest id is set to {ret[-1]["id"]}')
            self.latest_id = ret[-1]['id']

        return ret or []

    async def _fetch(self):
        return await self.twitter.get(self.endpoint, params=self.params)

class HomeTimelineSubscriber(Subscriber):
    subtype = SubsType.HomeTimeline
    endpoint = 'statuses/home_timeline'
    table_name = 'home_timeline'

class UserTimelineSubscriber(Subscriber):
    subtype = SubsType.UserTimeline
    endpoint = 'statuses/user_timeline'

    def __init__(self, twitter, channel_id, user_id=None, *, data=None):
        if not data:
            self.table_name = f'user_{user_id}'
            self.params = { 'user_id': user_id }
        
        super().__init__(twitter, channel_id, data=data)

class ListSubscriber(Subscriber):
    subtype = SubsType.List
    endpoint = 'lists/statuses'
    
    def __init__(self, twitter, channel_id, list_id=None, *, data=None):
        if not data:
            self.table_name = f'list_{list_id}'
            self.params = { 'list_id': list_id }
            
        super().__init__(twitter, channel_id, data=data)

class FavoriteSubscriber(Subscriber):
    subtype = SubsType.Favorite
    endpoint = 'favorites/list'

    def __init__(self, twitter, channel_id, user_id=None, *, data=None):        
        if not data:
            self.table_name = f'favorites_{user_id}'
            self.params = {
                'count': 50,
                'user_id': user_id
            }
        
        super().__init__(twitter, channel_id, data=data)
