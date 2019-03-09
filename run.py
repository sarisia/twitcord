import logging

from twitcord import Twitcord

#logging.basicConfig(level=logging.DEBUG, handlers=[logging.NullHandler()])
log = logging.getLogger()

# TODO: need launcher to handle signal
bot = Twitcord()
log.info("Starting")
bot.run()
