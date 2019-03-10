import logging

from twitcord import Twitcord

handler = logging.StreamHandler()
#handler.addFilter(lambda module: module.name.split('.')[0] in ['root', 'twitcord'])

logging.basicConfig(level=logging.DEBUG, handlers=[handler])
log = logging.getLogger()

# TODO: need launcher to handle signal
bot = Twitcord()
log.info("Starting")
bot.run()
