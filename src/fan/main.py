# encoding: utf-8
import sys

sys.path = [
    '/home/mixael/dev/pubsub_proto/src',
    '/home/mixael/dev/pubsub_proto/contrib/pymongo'
] + sys.path


if __name__ == '__main__':
    import fan.http.hub
