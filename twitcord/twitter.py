import functools
from logging import getLogger

from aioauth_client import TwitterClient

log = getLogger(__name__)


class TwitterWrapper(TwitterClient):
    async def _safe_request(self, method, endpoint, **kwargs):
        ret = None
        
        log.debug(f'Request: {method}, {endpoint}, {kwargs}')
        try:
            ret = await self.request(method, endpoint + '.json', **kwargs)
        except Exception as e:
            log.error(f'{method}, {endpoint}, {e}')

        return ret

    get = functools.partialmethod(_safe_request, 'GET')
    post = functools.partialmethod(_safe_request, 'POST')
