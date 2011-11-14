# encoding: utf-8
from twisted.python import log

class NoNews(Exception):
    pass


def log_failure(failure):
    log.msg(failure.getErrorMessage())
