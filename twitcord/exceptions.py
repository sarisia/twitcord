class TwitCordException(Exception):
    pass

class ConfigError(TwitCordException):
    pass
    
class TwitCordSignal(Exception):
    pass

class ExitSignal(TwitCordSignal):
    pass

class RestartSignal(TwitCordSignal):
    pass
