import uuid
import json
from zabbixapi import ZabbixApi
import zabbixapi_exception


class ZabbixAutomation(ZabbixApi):
    def __init__(self, url, automation_prefix):
        super(ZabbixAutomation, self).__init__(url)
        self.automation_prefix = automation_prefix
        self.debug_enabled = False

    def enable_debug(self, enabled):
        if enabled:
            self.debug_enabled = True

    def item_get(self, item_id=None, host_id=None, search_filter=None, output=None):
        try:
            items = self.item.get(output=output, hostids=host_id, itemids=item_id, search=search_filter)
            items_list = {"items": {}}
            items_counter = 0
            for item in items:
                items_list['items'].update({items_counter: item})
                items_counter += 1
        except Exception as ex:
            self.automation_exception(ex.message)
            return False
        return items_list

    def item_create(self,
                    item_key,
                    item_delay,
                    item_type,
                    item_value_type,
                    item_description,
                    host_id,
                    ):

        id_prefix = self.automation_prefix + '_'
        added_list = {'items': {}}
        added_counter = 0
        if type(host_id) is list:
            raise TypeError('only one host supported')

        host = self.host.get(output=['host', 'hostid'], hostids=host_id)[0]
        host.update(self.hostinterface.get(output='extend', filter={'main': 1, 'hostid': host_id})[0])
        try:
            added_item = self.item.create(name=id_prefix + str(uuid.uuid4()),
                                          key_=item_key,
                                          interfaceid=host['interfaceid'],
                                          hostid=host['hostid'],
                                          delay=item_delay,
                                          type=item_type,
                                          value_type=item_value_type,
                                          description=item_description
                                          )

            for item in added_item['itemids']:
                added_list['items'].update({added_counter: item})
                added_counter += 1

        except zabbixapi_exception.ZabbixIncompatibleApi as ex:
            self.automation_exception(ex.message)
            return False

        return added_list

    def item_delete(self, item_id):
        try:
            if type(item_id) is list or type(item_id) is tuple:
                removed_items = self.item.delete(*item_id)
            else:
                removed_items = self.item.delete(item_id)
            removed_list = {'items': {}}
            removed_counter = 0
            for item in removed_items['itemids']:
                removed_list['items'].update({removed_counter: item})
                removed_counter += 1

        except Exception as ex:
            self.automation_exception(ex.message)
            return False

        return removed_list

    def host_get(self, host_id=None, host_available=None, host_output=None, host_filter=None):

        hosts_list = {}
        if type(host_filter) is not list:
            tmp_host_filter = host_filter
            host_filter = [tmp_host_filter]

        if host_available is True:
            host_filter.append({'available': 1})
        elif host_available is False:
            host_filter.append({'available': 2})
        else:
            pass

        try:
            hosts = self.host.get(output=host_output, hostids=host_id, filter=host_filter)
            host_counter = 0
            for host in hosts:
                hosts_list.update({host_counter: host})
                host_counter += 1
        except Exception as ex:
            self.automation_exception(ex.message)
            return False

        return hosts_list

    def host_delete(self, host_id):
        try:
            deleted_list = {"deleted": {}}
            """ here we need to split in order to avoid any strange arg behaviours"""
            if host_id is list or host_id is tuple:
                deleted = self.host.delete(*host_id)
            else:
                deleted = self.host.delete(host_id)
            deleted_counter = 0
            for hostid in deleted['hostids']:
                deleted_list['deleted'].update({deleted_counter: hostid})
                deleted_counter += 1

        except Exception as ex:
            self.automation_exception(ex.message)
            return False
        return deleted_list

    def interface_get(self, host_id=None, only_main=False):
        interfaces_filter = {}
        interfaces_list = {}
        if host_id is not None:
            interfaces_filter = {'hostid': host_id}

        if only_main is True:
            interfaces_filter.update({'main': 1})

        try:
            interfaces = self.hostinterface.get(output='extend',
                                                filter=interfaces_filter)
            for interface in interfaces:
                interfaces_list.update({interface['hostid']: {}})

            for interface in interfaces:
                interfaces_list[interface['hostid']].update({interface['interfaceid']: interface})

        except Exception as ex:
            self.automation_exception(ex.message)
            return False

        return interfaces_list

    def metrics_get(self, host_id=None):
        metrics = {}
        items = None
        metrics_counter = 0
        try:
            hosts = self.host.get(output=['host', 'hostid'], hostids=host_id, filter={'available': 1})
            for host in hosts:
                items = self.item.get(output=['hostid', 'key_', 'lastvalue',
                                              'description', 'state', 'lastclock'],
                                      hostids=host['hostid'],
                                      selectHosts={"output": "name"})

            if items is None:
                raise ValueError('No item found for host ' + str(host_id))
            else:
                for item in items:
                    metric_string = '{}.{}'.format(item['hosts'][0]['name'], item['key_'])
                    metrics.update({metrics_counter: '{} {} {}'.format(metric_string,
                                                                       item['lastvalue'], item['lastclock'])})
                    metrics_counter += 1

        except Exception as ex:
            self.automation_exception(ex.message)
            return False

        return metrics

    def problem_get(self, acknowledged=False):

        problems = {}
        """ here we want to check for problem from zabbix triggers """
        problem_counter = 0
        for problem in self.problem.get(output=['eventid', 'clock'], acknowledged=acknowledged):
            status = {}
            event = self.event.get(output=('acknowledged', 'hosts', 'clock'),
                                   selectHosts=({'output': 'host'}),
                                   selectRelatedObject=({'output': 'description'}),
                                   filter=({'eventid': problem['eventid']}))

            status.update({'hostname': event[0]['hosts'][0]['host']})
            status.update({'acknowledged': event[0]['acknowledged']})
            status.update({'description': event[0]['relatedObject']['description']})
            status.update({'issued': problem['clock']})
            problems.update({problem_counter: status})
            problem_counter += 1

        return problems

    def create_action(self, alert_service, alert_script, action_template):

        media_created = False
        group_created = False
        user_created = False

        try:
            template_file = open(action_template)
            template = json.load(template_file)
            template_file.close()
        except Exception as ex:
            print ex.message
            return None

        def rollback(self):
            # if a media exist delete it
            if media_created:
                print('Rolling back mediatype {}'.format(mediatype))
                self.mediatype.delete(mediatype)
            if user_created:
                print('Rolling back user {}'.format(user))
                self.user.delete(user)
            if group_created:
                print('Rolling back group {}'.format(group))
                self.usergroup.delete(group)

        # first create a mediatype
        try:
            mediatype = self.mediatype.create(type=1,
                                              description=self.automation_prefix + '_notification',
                                              exec_path=alert_script,
                                              status=0,
                                              exec_params=alert_service + "\n{ALERT.SUBJECT}\n{ALERT.MESSAGE}\n",
                                              maxsessions=1,
                                              maxattempts=3,
                                              attempt_interval="10s"
                                              )['mediatypeids'][0]
            media_created = True
        except Exception as ex:
            print ex.message
            return None

        # add a custom group
        try:
            group = self.usergroup.create(name=self.automation_prefix + '_automation_group',
                                          gui_access=2
                                          )['usrgrpids'][0]
            group_created = True
        except Exception as ex:
            print ex.message
            rollback(self)
            return None

        # create user
        try:
            user = self.user.create(alias=self.automation_prefix + "_user",
                                    passwd=str(uuid.uuid4()),
                                    usrgrps=[{"usrgrpid": group}],
                                    user_medias=[{"mediatypeid": mediatype,
                                                  "sendto": self.automation_prefix,
                                                  "active": 0,
                                                  "severity": 63,
                                                  "period": "1-7,00:00-24:00"}],
                                    type=3)['userids'][0]   # must be a super-user least privilege doesn't apply here!
            user_created = True
        except Exception:
            print "Exception user already exists"
            rollback(self)
            return None

        try:
            template['name'] = self.automation_prefix + "_notify_all"
            template['operations'][0]['opmessage']['mediatypeid'] = mediatype
            template['operations'][0]['opmessage_usr'][0]['userid'] = user
            action = self.action.create(template)
        except Exception as ex:
            print ex.message
            rollback(self)
            return None

        return action

    def destroy_action(self):

        try:
            user = self.user.get(output="userid",
                                 filter={"alias": self.automation_prefix + "_user"})[0]['userid']
            group = self.usergroup.get(output="usrgrpid",
                                       filter={"name": self.automation_prefix + "_automation_group"})[0]['usrgrpid']
            mediatype = self.mediatype.get(output="mediatypeid",
                                           filter={"description": self.automation_prefix + "_notification"})[0]['mediatypeid']
            action = self.action.get(output="actionid",
                                     filter={"name": self.automation_prefix + "_notify_all"})[0]['actionid']
        except Exception as ex:
            print "Cannot find objects to destroy " + ex.message
            return False

        if user and group and mediatype and action:
            try:
                self.action.delete(action)
                self.user.delete(user)
                self.usergroup.delete(group)
                self.mediatype.delete(mediatype)
            except Exception as ex:
                print ex.message
                return False
            return True
        return False

    @staticmethod
    def automation_exception(exception):
        print('Oh oh something went wrong: {}'.format(exception))

    @staticmethod
    def mooncloud_json(result):
        if result is not False:
            json_result = {"data": result, "success": True}
        else:
            json_result = {'data': "Error occurred please check logs.", "success": False}

        print(json.dumps(json_result))
        return json.dumps(json_result)
