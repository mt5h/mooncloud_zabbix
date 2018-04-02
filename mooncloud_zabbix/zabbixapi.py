import requests
import json
import uuid
from zabbixapi_exception import ZabbixIncompatibleApi
from zabbixapi_exception import ZabbixNotPermitted


class ZabbixApi(object):
    """
    main zabbix api class it calls zabbix api and allow to set basic headers connection
    timeout and ssl certificate validation. It also supports dynamic method binding so
    we don't have to define every api call but we can model them following the Zabbix doc
    https://www.zabbix.com/documentation/3.4/manual/api
    """
    def __init__(self, url, json_rpc='2.0', content_type='application/json-rpc', invalid_cert=False, timeout=7, enable_debug=False):
        self.url = url.rstrip('/') + '/api_jsonrpc.php'
        self.content_type = content_type
        self.json_rpc = json_rpc
        self.token = None
        self.version = None
        self.timeout = timeout
        self.ssl_verify = invalid_cert
        self.debug_enabled = enable_debug

    def call_api(self, method, headers, body):

        """
        this function handle all api call to zabbix server and automatically insert
        id and auth token if it exists
        """

        call_id = str(uuid.uuid4())

        if body is not None:
            body.update({'id': call_id})

            if self.token is not None:
                body.update({'auth': self.token})

        if self.debug_enabled:
            print('\033[92m[DEBUG request]: {}\033[0m'.format(json.dumps(body)))
        try:
            if method == 'post':
                response = requests.post(self.url, headers=headers, data=json.dumps(body), verify=self.ssl_verify,
                                         timeout=self.timeout)
            elif method == 'get':
                response = requests.get(self.url, headers=headers, verify=self.ssl_verify, timeout=self.timeout)
            else:
                raise NotImplemented('Invalid method'.format(method))
            if self.debug_enabled:
                print('\033[92m[DEBUG response]: {}\033[0m'.format(response.text))

        except Exception as ex:
            print("\033[91m[ERROR]: {}\033[0m".format(ex.message))
            response = {'result': ex.message}
            return response

        try:
            response.raise_for_status()

        except Exception:
            print("Bad return code {}".format(response.status_code))

        json_response = json.loads(response.text)

        try:
            if json_response['error']['code'] == -32602:
                raise ZabbixIncompatibleApi("\033[91m[ERROR]:{} code {}\033[0m".format(json_response['error']['data'],
                                                                                 json_response['error']['code']))
            if json_response['error']['code'] == -32500:
                raise ZabbixNotPermitted("\033[91m[ERROR]:{} code {}\033[0m".format(json_response['error']['data'],
                                                                              json_response['error']['code']))

        except KeyError:
            pass

        return json_response['result']

    # todo create api version control

    def get_info(self):

        headers = {'Content-Type': self.content_type}
        params = {
            'jsonrpc': self.json_rpc,
            'method': 'apiinfo.version',
            'params': {}
        }

        r = self.call_api('post', headers, params)
        self.version = r

    def login(self, username, password):

        headers = {'Content-Type': self.content_type}
        params = {
            'jsonrpc': self.json_rpc,
            'method': 'user.login',
            'params': {'user': username, 'password': password},
        }

        r = self.call_api('post', headers, params)

        if type(r) is str or type(r) is unicode:
            self.token = r
        else:
            self.token = None
        return True

    def logout(self):
        if self.token is not None:
            headers = {'Content-Type': self.content_type}
            params = {
                'jsonrpc': self.json_rpc,
                'method': 'user.logout',
                'params': {},
            }

            r = self.call_api('post', headers, params)
            if str(r).lower() == 'true':
                self.token = None
        else:
            return False
        return True

    def __getattr__(self, zbobj):

        """
        dynamic method binding with this function we can all
        every type of function and if it exists as Zabbix API we can
        call it directly without create a specific function for every method
        """
        return ZabbixAPICommonObj(zbobj, self)


class ZabbixAPICommonObj(object):
    def __init__(self, zbobj, parent):
        self.zbobj = zbobj
        self.parent = parent

    def __getattr__(self, zbmethod):
        # print('Calling __getattr__: {}'.format(zbmethod))
        self.zbmethod = zbmethod

        def get_arguments(*arg, **kw):

            """
            kw is a dictionary of key=value that fit
            perfectly in our params request body
            """
            #print('kw->{}'.format(kw))
            #print('arg->{}'.format(arg))
            headers = {'Content-Type': self.parent.content_type}
            params = {
                'jsonrpc': self.parent.json_rpc,
                'method': self.zbobj + '.' + self.zbmethod,
                'params': kw or arg
            }
            r = self.parent.call_api('post', headers, params)
            # todo create a debug mode to print call details
            #print('{}'.format(r))
            return r
        return get_arguments
