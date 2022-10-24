class NotSendingError(Exception):
    pass


class SendMessageError(NotSendingError):
    pass


class RequestAPIError(Exception):
    pass


class HTTPError(Exception):
    pass


class CurrentTimeError(NotSendingError):
    pass


class JSONDecodeError(Exception):
    pass
