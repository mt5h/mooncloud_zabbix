import sys
import json
import argparse
from config import Parameter
from zabbixautomation import ZabbixAutomation


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="This utility implements Zabbix APIs \\"
                                                 "and perform some basic tasks")
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
    parser.add_argument("--additem", action="store_true",
                        help="add item in configuration")
    parser.add_argument("--delitem", action="store", type=int,
                        help="delete an item")
    parser.add_argument("-f", "--listint", action="store_true",
                        help="list all interfaces")
    parser.add_argument("-p", "--problems", action="store_true",
                        help="list all problems")
    parser.add_argument("-m", "--metrics", action="store_true",
                        help="list items value as metrics")
    parser.add_argument("--addalert", action="store_true",
                        help="set alert action")
    parser.add_argument("--delalert", action="store_true",
                        help="remove alert action")
    parser.add_argument("--extend", action="store_true",
                        help="show full output")
    args = parser.parse_args()

    if not args.verbose:
        sys.tracebacklimit = 0

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

    if args.verbose:
        session.enable_debug(True)

    session.login(username=username, password=password)

    if args.listhosts:
        if args.extend:
            output = 'extend'
        else:
            output = ['name', 'available']
        hosts = session.host_get(host_output=output, host_available=None, host_id=args.hostid)
        result = hosts

    if args.listitems:
        if args.extend:
            output = 'extend'
        else:
            output = ['description', 'lastvalue']

        items = session.item_get(host_id=args.hostid, output=output)
        result = items

    if args.listint:
        interfaces = session.interface_get(host_id=args.hostid)
        result = interfaces

    if args.problems:
        problems = session.problem_get(acknowledged=False)
        result = problems

    if args.metrics:
        metrics = session.metrics_get(host_id=args.hostid)
        result = metrics

    if args.addalert:
        alert = session.create_action(notification_endpoint,
                                        notification_script,
                                        notification_template)
        result = alert

    if args.delalert:
        alert = session.destroy_action()
        result = alert

    if args.additem:
        result = {}
        counter = 0
        hosts = session.host_get(host_output=['name', 'available'], host_available=None, host_id=args.hostid)
        for host in hosts.itervalues():
            for key, value in items.items():
                items = session.item_create(host_id=host['hostid'],
                                          item_key=value['key'],
                                          item_delay=value['delay'],
                                          item_description=value['description'],
                                          item_type=value['type'],
                                          item_value_type=value['value_type']
                                          )
                result.update({counter: items})
                counter += 1

    if args.delitem:
        item = session.item_delete(args.delitem)
        result = item

    print json.dumps(result, indent=2, sort_keys=True)
    session.logout()

