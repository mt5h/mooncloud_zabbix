

class ZabbixApiException(Exception):
    def __init__(self, message):

        super(ZabbixApiException, self).__init__(message)


class ZabbixNotAuthenticated(ZabbixApiException):
    def __init__(self, message):

        super(ZabbixNotAuthenticated, self).__init__(message)


class ZabbixIncompatibleApi(ZabbixApiException):
    def __init__(self, message):

        super(ZabbixIncompatibleApi, self).__init__(message)

class ZabbixNotPermitted(ZabbixApiException):
    def __init__(self, message):

        super(ZabbixNotPermitted, self).__init__(message)