#!/usr/bin/env python
# # -*- coding: utf-8 -*-

import sys
import json
import argparse
from config import Parameter
from zabbixautomation import ZabbixAutomation


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Perform some basic tasks using Zabbix APIs " +
                                                 "launch without args (except configuration) " +
                                                 "to test the connection")
    parser.add_argument("-c", "--config", type=str,
                        help="configuration file", default="config.json")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    parser.add_argument("-i", "--hostid", action="store", type=int,
                        help="set specific host")
    parser.add_argument("-l", "--listhosts", action="store_true",
                        help="list all hosts active on Zabbix")
    parser.add_argument("-t", "--listitems", action="store_true",
                        help="list all items")
    parser.add_argument("-f", "--listint", action="store_true",
                        help="list all interfaces")
    parser.add_argument("-p", "--problems", action="store_true",
                        help="list all problems")
    parser.add_argument("-m", "--metrics", action="store_true",
                        help="list items value as metrics")
    parser.add_argument("--add-item", action="store_true", dest='additem',
                        help="add all items in configuration")
    parser.add_argument("--del-item", action="store", type=int, dest='delitem',
                        help="delete the item specified as DELITEM")
    parser.add_argument("--add-alert", action="store_true", dest='addalert',
                        help="set alert action")
    parser.add_argument("--del-alert", action="store_true", dest='delalert',
                        help="remove alert action")
    parser.add_argument("--extend", action="store_true",
                        help="show full output")
    args = parser.parse_args()

    if not args.verbose:
        sys.tracebacklimit = 0

    login_success = False
    logout_success = False
    action_specified = False

    conf = Parameter(args.config)
    credentials = conf.get('zabbix_credentials')
    url = credentials['zabbix_url']
    username = credentials['zabbix_username']
    password = credentials['zabbix_password']
    settings = conf.get('zabbix_api_settings')
    prefix = settings['system_prefix']
    probe_wait = settings['system_probe_wait']
    debug = settings['enable_debug']
    notification_template = settings['action_template']
    notification_script = settings['notification_script']
    notification_endpoint = settings['notification_endpoint']
    items = conf.get('zabbix_items')

    session = ZabbixAutomation(url=url, automation_prefix=prefix)
    result = None

    if args.verbose:
        session.enable_debug(True)

    login_success = session.login(username=username, password=password)

    if args.listhosts:
        action_specified = True
        if args.extend:
            output = 'extend'
        else:
            output = ['name', 'available']
        result = session.host_get(host_output=output, host_available=None, host_id=args.hostid)

    if args.listitems:
        action_specified=True
        if args.extend:
            output = 'extend'
        else:
            output = ['description', 'lastvalue']

        result = session.item_get(host_id=args.hostid, output=output)

    if args.listint:
        action_specified=True
        result = session.interface_get(host_id=args.hostid)

    if args.problems:
        action_specified=True
        result = session.problem_get(acknowledged=False)

    if args.metrics:
        action_specified=True
        result = session.metrics_get(host_id=args.hostid)

    if args.addalert:
        action_specified=True
        result = session.create_action(notification_endpoint,
                                        notification_script,
                                        notification_template)

    if args.delalert:
        action_specified=True
        result = session.destroy_action()

    if args.additem:
        action_specified=True
        result = {}
        counter = 0
        hosts = session.host_get(host_output=['name', 'available'], host_available=None, host_id=args.hostid)
        for host in hosts.itervalues():
            for key, value in items.items():
                items=session.item_create(host_id=host['hostid'],
                                          item_key=value['key'],
                                          item_delay=value['delay'],
                                          item_description=value['description'],
                                          item_type=value['type'],
                                          item_value_type=value['value_type']
                                          )
                result.update({counter: items})
                counter += 1

    if args.delitem:
        action_specified=True
        result = session.item_delete(args.delitem)

    if result is True:
        result = "Success!"
    elif result is False:
        result = "Failed!"
    elif result == {}:
        result = "Empty response"

    logout_success = session.logout()

    if login_success and logout_success:
        if not action_specified:
            print 'No action specified use -h to show usage'
            print '\033[92mConnection success\033[0m'
        else:
            print '\033[94m'+json.dumps(result, indent=2, sort_keys=True) + '\033[0m'
    else:
        print '\033[91mConnection failed\033[0m'
