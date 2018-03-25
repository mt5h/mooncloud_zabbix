import json
from future.utils import raise_from


class Config(object):
    def __init__(self, config_file):
        self.config_file = config_file
        self.file = None
        try:
            self.file = open(config_file)
            self.file.close()

        except IOError as exc:
            raise_from(IOError('failed to open {}'.format(config_file)), exc)


class Parameter(Config):
    def __init__(self, config_file):
        super(Parameter, self).__init__(config_file)

    def get(self, custom_key):
        conf = json.load(open(self.config_file))
        for key, value in conf.items():
            if custom_key == key:
                return value
        raise KeyError("{} not found".format(custom_key))
