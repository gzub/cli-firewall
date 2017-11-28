"""
Copyright 2017 Akamai Technologies, Inc. All Rights Reserved.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

"""
This code leverages akamai OPEN API. to control Certificates deployed in Akamai Network.
In case you need quick explanation contact the initiators.
Initiators: vbhat@akamai.com, aetsai@akamai.com, mkilmer@akamai.com
"""

import json
from akamai.edgegrid import EdgeGridAuth
from firewallruleswrapper import fireShield
import argparse
import configparser
import requests
import os
import logging
import shutil
import sys
from prettytable import PrettyTable
from akamai.edgegrid import EdgeGridAuth, EdgeRc


PACKAGE_VERSION = "0.1.0"

# Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs')
log_file = os.path.join('logs', 'akamai-firewall-rules.log')

# Set the format of logging in console and file separately
log_formatter = logging.Formatter(
    "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
console_formatter = logging.Formatter("%(message)s")
root_logger = logging.getLogger()

logfile_handler = logging.FileHandler(log_file, mode='w')
logfile_handler.setFormatter(log_formatter)
root_logger.addHandler(logfile_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)
# Set Log Level to DEBUG, INFO, WARNING, ERROR, CRITICAL
root_logger.setLevel(logging.INFO)


def init_config(edgerc_file, section):
    if not edgerc_file:
        if not os.getenv("AKAMAI_EDGERC"):
            edgerc_file = os.path.join(os.path.expanduser("~"), '.edgerc')
        else:
            edgerc_file = os.getenv("AKAMAI_EDGERC")

    if not os.access(edgerc_file, os.R_OK):
        root_logger.error("Unable to read edgerc file \"%s\"" % edgerc_file)
        exit(1)

    if not section:
        if not os.getenv("AKAMAI_EDGERC_SECTION"):
            section = "firewall"
        else:
            section = os.getenv("AKAMAI_EDGERC_SECTION")

    try:
        edgerc = EdgeRc(edgerc_file)
        base_url = edgerc.get(section, 'host')

        session = requests.Session()
        session.auth = EdgeGridAuth.from_edgerc(edgerc, section)

        return base_url, session
    except configparser.NoSectionError:
        root_logger.error("Edgerc section \"%s\" not found" % section)
        exit(1)
    except Exception:
        root_logger.info(
            "Unknown error occurred trying to read edgerc file (%s)" %
            edgerc_file)
        exit(1)

def cli():
    prog = get_prog_name()
    if len(sys.argv) == 1:
        prog += " [command]"

    parser = argparse.ArgumentParser(
        description='Akamai CLI for Siteshield and Firewall Notifications',
        add_help=False,
        prog=prog)
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' +
                PACKAGE_VERSION)

    subparsers = parser.add_subparsers(
        title='Commands', dest="command", metavar="")

    actions = {}

    subparsers.add_parser(
        name="help",
        help="Show available help",
        add_help=False).add_argument(
        'args',
        metavar="",
        nargs=argparse.REMAINDER)


    actions["list_services"] = create_sub_command(
        subparsers, "list-services", "List all Maps",
         None,
         None)

    actions["list_subscriptions"] = create_sub_command(
        subparsers, "list-subscriptions", "List all Maps",
         None,
         None)

    actions["subscribe"] = create_sub_command(
        subparsers, "subscribe",
        "Subscribe to the firewall notification list ",
        [{"name": "serviceName", "help": "Name of the service to be subscribed to within SINGLE quotes"},
         {"name": "serviceId", "help": "ID of the service to be subscribed to"}],
         [{"name": "email", "help": "Email Id of the subscriber"}])

    actions["unsubscribe"] = create_sub_command(
        subparsers, "unsubscribe",
        "Unsubscribe to the firewall notification list ",
        [{"name": "serviceName", "help": "Name of the service to be subscribed to within SINGLE quotes"},
         {"name": "serviceId", "help": "ID of the service to be subscribed to"}],
          None)

    actions["list_cidrs"] = create_sub_command(
        subparsers, "list-cidrs",
        "List the CIDR block ",
        [{"name": "serviceName", "help": "Name of the service within SINGLE quotes"},
         {"name": "serviceId", "help": "Id of the service"}],
          None)

    actions["list_ss_maps"] = create_sub_command(
        subparsers, "list-ss-maps",
        "List the siteshield maps ",
          None,
          None)

    actions["list_ss_cidrs"] = create_sub_command(
        subparsers, "list-ss-cidrs",
        "List the CIDR blocks ",
        [{"name": "mapName", "help": "Name of the map within SINGLE quotes"},
         {"name": "mapId", "help": "ID of the map"}],
          None)

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help()
        return 0

    if args.command == "help":
        if len(args.args) > 0:
            if actions[args.args[0]]:
                actions[args.args[0]].print_help()
        else:
            parser.prog = get_prog_name() + " help [command]"
            parser.print_help()
        return 0

    return getattr(sys.modules[__name__], args.command.replace("-", "_"))(args)

def create_sub_command(
        subparsers,
        name,
        help,
        optional_arguments=None,
        required_arguments=None):
    action = subparsers.add_parser(name=name, help=help, add_help=False)

    if required_arguments:
        required = action.add_argument_group("required arguments")
        for arg in required_arguments:
            name = arg["name"]
            del arg["name"]
            required.add_argument("--" + name,
                                  required=True,
                                  **arg,
                                  )

    optional = action.add_argument_group("optional arguments")
    if optional_arguments:
        for arg in optional_arguments:
            name = arg["name"]
            del arg["name"]
            if name == 'force' or name == 'showExpiration':
                optional.add_argument(
                    "--" + name,
                    required=False,
                    **arg,
                    action="store_true")
            else:
                optional.add_argument("--" + name,
                                      required=False,
                                      **arg,
                                      )

    optional.add_argument(
        "--edgerc",
        help="Location of the credentials file [$AKAMAI_EDGERC]",
        default=os.path.join(
            os.path.expanduser("~"),
            '.edgerc'))

    optional.add_argument(
        "--section",
        help="Section of the credentials file [$AKAMAI_EDGERC_SECTION]",
        default="firewall")

    optional.add_argument(
        "--debug",
        help="DEBUG mode to generate additional logs for troubleshooting",
        action="store_true")

    return action

# Override log level if user wants to run in debug mode
# Set Log Level to DEBUG, INFO, WARNING, ERROR, CRITICAL
'''if args.debug:
    root_logger.setLevel(logging.DEBUG)'''

def list_services(args):
    base_url, session = init_config(args.edgerc, args.section)
    fireShieldObject = fireShield(base_url)
    root_logger.info('Fetching the services related information.')
    listServicesResponse = fireShieldObject.listServices(session)
    if listServicesResponse.status_code == 200:
        #root_logger.info(json.dumps(listServicesResponse.json(), indent=4))
        table = PrettyTable(['Service ID', 'Service Name', 'Service Description'])
        table.align ="l"

        for eachItem in listServicesResponse.json():
            rowData = []
            serviceId = eachItem['serviceId']
            serviceName = eachItem['serviceName']
            description = eachItem['description']
            rowData.append(serviceId)
            rowData.append(serviceName)
            rowData.append(description)
            table.add_row(rowData)
        root_logger.info(table)
    else:
        root_logger.info('There was error in fetching response. Use --debug to know more.')
        root_logger.debug(json.dumps(listServicesResponse.json(), indent=4))

def list_subscriptions(args):
    base_url, session = init_config(args.edgerc, args.section)
    fireShieldObject = fireShield(base_url)
    root_logger.info('Fetching the subscription related information.')
    list_subscriptionsResponse = fireShieldObject.listSubscriptions(session)
    #root_logger.info(json.dumps(list_subscriptionsResponse.json(), indent=4))
    if list_subscriptionsResponse.status_code == 200:
        #root_logger.info(json.dumps(listServicesResponse.json(), indent=4))
        table = PrettyTable(['Service ID', 'Service Name', 'Service Description', 'Email', 'Sign-up-Date'])
        table.align ="l"

        for eachItem in list_subscriptionsResponse.json()['subscriptions']:
            rowData = []
            rowData.append(eachItem['serviceId'])
            rowData.append(eachItem['serviceName'])
            rowData.append(eachItem['description'])
            rowData.append(eachItem['email'])
            rowData.append(eachItem['signupDate'])
            table.add_row(rowData)
        root_logger.info(table)
    else:
        root_logger.info('There was error in fetching response. Use --debug to know more.')
        root_logger.debug(json.dumps(listServicesResponse.json(), indent=4))


def subscribe(args):
    if args.serviceId and args.serviceName:
        root_logger.info('You cannot specify both serviceId and serviceName. Enter any one of them.')
        exit(-1)
    if not args.serviceId and not args.serviceName:
        root_logger.info('Specify either of serviceId or serviceName.')
        exit(-1)

    base_url, session = init_config(args.edgerc, args.section)
    fireShieldObject = fireShield(base_url)
    root_logger.info('Fetching the services related information to validate.\n')

    validService = False
    listServicesResponse = fireShieldObject.listServices(session)
    if listServicesResponse.status_code == 200:
        for eachItem in listServicesResponse.json():
            if args.serviceId:
                if int(args.serviceId) == int(eachItem['serviceId']):
                    validService = True
                    serviceId = args.serviceId
                    break
            if args.serviceName:
                if args.serviceName == eachItem['serviceName']:
                    validService = True
                    serviceId = eachItem['serviceId']
                    break
    else:
        root_logger.info('There was error in fetching services response. Use --debug to know more.')
        root_logger.debug(json.dumps(listServicesResponse.json(), indent=4))

    if validService is False:
        root_logger.info('Entered serviceId or serviceName is Invalid. Please check using list-services\n')
        exit(-1)
    else:
        root_logger.info('Service Information provided is valid. Proceeding to update subscription.\n')
        list_subscriptionsResponse = fireShieldObject.listSubscriptions(session)
        if list_subscriptionsResponse.status_code == 200:
            #Proceed to update the subscriptions
            newSubscription = {}
            newSubscription['email'] = args.email
            newSubscription['serviceId'] = int(serviceId)
            subscriptionData = list_subscriptionsResponse.json()
            subscriptionData['subscriptions'].append(newSubscription)
            #root_logger.info(json.dumps(subscriptionData, indent=4))
            updateSubscriptionsRespose = fireShieldObject.updateSubscriptions(session, json.dumps(subscriptionData))
            if updateSubscriptionsRespose.status_code == 200:
                root_logger.info('Subscription updated Successfully\n')
            else:
                root_logger.info(json.dumps(updateSubscriptionsRespose.json(), indent=4))
        else:
            root_logger.info('There was error in fetching subscription response. Use --debug to know more.')
            root_logger.debug(json.dumps(listServicesResponse.json(), indent=4))

def unsubscribe(args):
    if args.serviceId and args.serviceName:
        root_logger.info('You cannot specify both serviceId and serviceName. Enter any one of them.')
        exit(-1)
    if not args.serviceId and not args.serviceName:
        root_logger.info('Specify either of serviceId or serviceName.')
        exit(-1)

    base_url, session = init_config(args.edgerc, args.section)
    fireShieldObject = fireShield(base_url)
    root_logger.info('Fetching the services related information to validate.\n')

    list_subscriptionsResponse = fireShieldObject.listSubscriptions(session)
    validService = False
    if list_subscriptionsResponse.status_code == 200:
        subscriptionData = list_subscriptionsResponse.json()

        #Using Index to iterate and delete the item from list
        index = 0
        for everySubscription in subscriptionData['subscriptions']:
            if args.serviceId:
                if int(args.serviceId) == int(everySubscription['serviceId']):
                    validService = True
                    serviceName = everySubscription['serviceName']
                    del subscriptionData['subscriptions'][index]
                    break
            if args.serviceName:
                if args.serviceName == everySubscription['serviceName']:
                    validService = True
                    serviceName = everySubscription['serviceName']
                    del subscriptionData['subscriptions'][index]
                    break
            index += 1

        #root_logger.info(json.dumps(subscriptionData, indent=4))
        if validService is True:
            root_logger.info('Updating the subscription by unsubscribing to: ' + serviceName)
            updateSubscriptionsRespose = fireShieldObject.updateSubscriptions(session, json.dumps(subscriptionData))
            if updateSubscriptionsRespose.status_code == 200:
                root_logger.info('Subscription updated Successfully\n')
            else:
                root_logger.info(json.dumps(updateSubscriptionsRespose.json(), indent=4))
        else:
            root_logger.info('Given serviceId or serviceName is invalid. Run listSubscriptions to know valid subscriptions\n')
            exit(-1)
    else:
        root_logger.info('There was error in fetching subscription response. Use --debug to know more.')
        root_logger.debug(json.dumps(listServicesResponse.json(), indent=4))

def list_cidrs(args):
    base_url, session = init_config(args.edgerc, args.section)
    fireShieldObject = fireShield(base_url)
    root_logger.info('Fetching the CIDR blocks related information.')
    list_cidrResponse = fireShieldObject.listCidr(session)
    #root_logger.info(json.dumps(list_cidrResponse.json(), indent=4))
    if list_cidrResponse.status_code == 200:
        #root_logger.info(json.dumps(listServicesResponse.json(), indent=4))
        table = PrettyTable(['CIDR Block', 'Port', 'Activation Date', 'Status', 'Service Name'])
        table.align ="l"

        for eachItem in list_cidrResponse.json():
            rowData = []
            if args.serviceName:
                if args.serviceName == eachItem['serviceName']:
                    rowData.append(str(eachItem['cidr']) + str(eachItem['cidrMask']))
                    rowData.append(eachItem['port'])
                    rowData.append(eachItem['effectiveDate'])
                    rowData.append(eachItem['lastAction'])
                    rowData.append(eachItem['serviceName'])
                    table.add_row(rowData)
            elif args.serviceId:
                if str(args.serviceId) == str(eachItem['serviceId']):
                    rowData.append(str(eachItem['cidr']) + str(eachItem['cidrMask']))
                    rowData.append(eachItem['port'])
                    rowData.append(eachItem['effectiveDate'])
                    rowData.append(eachItem['lastAction'])
                    rowData.append(eachItem['serviceName'])
                    table.add_row(rowData)
            else:
                    rowData.append(str(eachItem['cidr']) + str(eachItem['cidrMask']))
                    rowData.append(eachItem['port'])
                    rowData.append(eachItem['effectiveDate'])
                    rowData.append(eachItem['lastAction'])
                    rowData.append(eachItem['serviceName'])
                    table.add_row(rowData)

        root_logger.info(table)
    else:
        root_logger.info('There was error in fetching response. Use --debug to know more.')
        root_logger.debug(json.dumps(list_cidrResponse.json(), indent=4))

def list_ss_maps(args):
    base_url, session = init_config(args.edgerc, args.section)
    fireShieldObject = fireShield(base_url)
    root_logger.info('Fetching the Siteshield Maps informations.\n')

    listMapsResponse = fireShieldObject.listMaps(session)

    if listMapsResponse.status_code == 200:
        #root_logger.info(json.dumps(listMapsResponse.json(), indent=4))
        table = PrettyTable(['Map ID', 'Map Name', 'Last Acknowledged By', 'Acknowledge Date', 'Contact Info'])
        table.align ="l"

        for eachItem in listMapsResponse.json()['siteShieldMaps']:
            rowData = []
            mapId = eachItem['mcmMapRuleId']
            ruleName = eachItem['ruleName']
            acknowledgedBy = eachItem['acknowledgedBy']
            acknowledgedOn = eachItem['acknowledgedOn']
            contacts = ''
            for eachContact in eachItem['contacts']:
                contacts = eachContact + ' ' + contacts
            rowData.append(mapId)
            rowData.append(ruleName)
            rowData.append(acknowledgedBy)
            rowData.append(acknowledgedOn)
            rowData.append(contacts)

            table.add_row(rowData)
        root_logger.info(table)
    else:
        root_logger.info('There was error in fetching response. Use --debug to know more.')
        root_logger.debug(json.dumps(listServicesResponse.json(), indent=4))

def list_ss_cidrs(args):
    if args.mapId and args.mapName:
        root_logger.info('You cannot specify both mapId and mapName. Enter any one of them.')
        exit(-1)
    if not args.mapId and not args.mapName:
        root_logger.info('Specify either of mapId or mapName.')
        exit(-1)
    base_url, session = init_config(args.edgerc, args.section)
    fireShieldObject = fireShield(base_url)
    root_logger.info('Fetching the Siteshield CIDR block information\n')

    listMapsResponse = fireShieldObject.listMaps(session)

    if listMapsResponse.status_code == 200:
        #root_logger.info(json.dumps(listMapsResponse.json(), indent=4))
        table = PrettyTable(['Map ID', 'Map Name', 'Last Acknowledged By', 'Acknowledge Date', 'Contact Info'])
        table.align ="l"

        mapFound = False
        for eachItem in listMapsResponse.json()['siteShieldMaps']:
            if args.mapName:
                if eachItem['ruleName'] == args.mapName:
                    root_logger.info('Current CIDR blocks are: ')
                    for eachAddress in eachItem['currentCidrs']:
                        root_logger.info(eachAddress)
                    mapFound = True
            elif args.mapId:
                if str(eachItem['mcmMapRuleId']) == str(args.mapId):
                    root_logger.info('Current CIDR blocks are: ')
                    for eachAddress in eachItem['currentCidrs']:
                        root_logger.info(eachAddress)
                    mapFound = True

        if mapFound is False:
            root_logger.info('Unable to find the map. Please check the name/Id')
            exit(-1)

    else:
        root_logger.info('There was error in fetching response. Use --debug to know more.')
        root_logger.debug(json.dumps(listServicesResponse.json(), indent=4))

def get_prog_name():
    prog = os.path.basename(sys.argv[0])
    if os.getenv("AKAMAI_CLI"):
        prog = "akamai firewall"
    return prog

def get_cache_dir():
    if os.getenv("AKAMAI_CLI_CACHE_DIR"):
        return os.getenv("AKAMAI_CLI_CACHE_DIR")

    return os.curdir

# Final or common Successful exit
if __name__ == '__main__':
    try:
        status = cli()
        exit(status)
    except KeyboardInterrupt:
        exit(1)