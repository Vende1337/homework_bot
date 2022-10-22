class NotSendingError(Exception):
    pass


class SendMessageError(NotSendingError):
    pass


class RequestAPIError(Exception):
    pass


class HTTPError(NotSendingError):
    pass


class JSONDecodeError(Exception):
    pass
