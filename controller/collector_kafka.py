import argparse
import time
import socket
import struct
import binascii
import pprint
import logging
from copy import copy
import io
import json
import requests
import subprocess
from influxdb import InfluxDBClient
from confluent_kafka import Producer


BASE_URL = "http://10.160.3.213:3001"
TOKEN_URL = f"{BASE_URL}/issueJwtToken"
POST_URL = f"{BASE_URL}/api/transactions/storePoT"

# Log configuration
log_format = "[%(asctime)s] [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format, filename="logs/int_collector.log")
logger = logging.getLogger('int_collector')

first = True
current_timestamp = 0

# Kafka configuration
kafka_conf = {'bootstrap.servers': '10.160.3.213:9092'}
kafka_producer = Producer(kafka_conf)
kafka_topic = "PoT-tests"


def get_jwt_token():
    """Fetch JWT token from the API."""
    try:
        response = requests.get(TOKEN_URL)
        if response.status_code == 200:
            token = response.json().get("data") #because it is being saved as data:
            logger.info("Successfully obtained JWT token.")
            logger.info("Token received: %s",token)
            return token
        else:
            logger.info("Failed to obtain JWT token: %s", response.text)
            return None
    except Exception as e:
        logger.info("Exception while fetching JWT token: %s", e)
        return None

JWT_TOKEN = get_jwt_token()

def get_updated_geolocation():
    try:
        command = 'curl -s "http://ipinfo.io/$(curl -s ifconfig.me)/json"'
        result = subprocess.check_output(command, shell=True)
        data = json.loads(result.decode('utf-8'))
        geolocation = "10.1.2.0/24,{country},{region},{city},{loc},50".format(
            country=data.get("country", "Unknown"),
            region=data.get("region", "Unknown"),
            city=data.get("city", "Unknown"),
            loc=data.get("loc", "Unknown")
        )
        logger.info("Updategeolocation: %s", geolocation)
        return geolocation
    except Exception as e:
        logger.exception("Fail obtaining the geolocation: %s", e)
        return "10.1.2.0/24,Unknown,Unknown,Unknown,0,0,50"


class IntReport():
    def __init__(self, data, address):
        # Format of received report
        fmt = '!3sBIQIb'
        self.int_report_hdr = data

        # Save each parameter in a variable
        (self.service_path_identifier, self.service_index, self.rnd, self.cml, self.seq_number, self.dropped) = struct.unpack(fmt, self.int_report_hdr)
        self.service_path_identifier = int.from_bytes(self.service_path_identifier, byteorder='big', signed=False)
        self.address = address

        global first
        global current_timestamp
        # Set to zero the timestamp of the first received packet
        if first:
            first = False
            self.timestamp = 0
            current_timestamp = int(time.time() * 1e3)
        else:
            self.timestamp = int(time.time() * 1e3) - current_timestamp

        logger.debug(vars(self))

class IntCollector():
    
    def __init__(self, influx, period):
        self.influx = influx
        self.reports = []  # list of reports
        self.period = period  # maximum time delay of int report sending to influx
        self.last_send = time.time()  # last time when reports were sent to influx
        
    def add_report(self, report):
        self.reports.append(report)
        
        reports_cnt = len(self.reports)
        logger.debug('%d reports ready to be sent' % reports_cnt)
        # send if several reports are ready to send or some time has passed since the last sending
        if reports_cnt > (2 * args.count - 1):
            logger.info("Sending %d reports to influx and Kafka from last %s secs" % (reports_cnt, time.time() - self.last_send))
            self._send_reports()
            self.last_send = time.time()
            
    def _prepare_reports(self, report, exclude_keys=None):
        # Report structure
        json_report = {
            "measurement": "int_telemetry",
            'time': report.timestamp,
            "fields": {
                "CML": report.cml,
                "Dropped": report.dropped,
                "Geolocation": get_updated_geolocation(), 
                "RND": report.rnd,
                "sequenceNumber": report.seq_number,
                "serviceIndex": report.service_index,
                "servicePathIdentifier": report.service_path_identifier,
                "serviceID": "57310caf-bcc4-4008-82b8-6cfa6263bbcd",
                "switchIP": report.address,
                "measurement": "int_telemetry",
                "time": report.timestamp
            }
        }
        
        if exclude_keys:
            for key in exclude_keys:
                json_report.pop(key, None)
            
        return json_report
        
    def _send_reports(self):
        global JWT_TOKEN
        json_body = []
        kafka_reports = []
        DLT_reports = []
        for report in self.reports:
            json_report = self._prepare_reports(report)
            json_body.append(json_report)
            kafka_reports.append(json.dumps(json_report))
            dlt_report= self._prepare_reports(report,exclude_keys=["measurement","time"])
            dlt_report2= dlt_report["fields"]
            DLT_reports.append(dlt_report2)

        logger.info("Json body for influx:\n %s" % pprint.pformat(json_body))
        if json_body:
            try:
                self.influx.write_points(json_body)
                logger.info(" %d int reports sent to the influx" % len(json_body))
            except Exception as e:
                logger.exception(e)

        # Send reports to Kafka
        for kafka_report in kafka_reports:
            try:
                kafka_producer.produce(kafka_topic, kafka_report)
            except Exception as e:
                logger.exception("Failed to send report to Kafka")

        kafka_producer.flush()
        self.reports = []  # clear reports sent
        
        
        # Send reports to the REST API
        if JWT_TOKEN:
            
            logger.info("Reports available: %s", len(self.reports))
            #logger.info("Report details: %s", self.reports)
            #logger.info("DLT: %s", len(DLT_reports))
            logger.info("Informacion enviada en categoryTrustSources a la DLT: %s", DLT_reports)

            #category_trust_sources = [self._prepare_reports(report) for report in self.reports]

            payload = {
                "dbPointer": "pointer",
                "categoryTrustSources": DLT_reports,  # antes category_trust_sources
                "oracleSignature": "signature",
                "timestamp": int(time.time())
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {JWT_TOKEN}"
            }

            try:
                response = requests.post(POST_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    logger.info("Successfully sent data to REST API: %s", response.json())
                    logger.info("Mensaje de prueba %s",DLT_reports)
                else:
                    logger.info("Failed to send data to REST API: %s", response.text)
            except Exception as e:
                logger.info("Exception while sending data to REST API: %s", e)
        else:
            logger.info("Skipping API call: JWT token is missing.")

def unpack_int_report(packet, address):
    report = IntReport(packet, address)
    logger.info(report)
    return report
            
def influx_client(args):
    if ':' in args.host:
        host, port = args.host.split(':')
    else:
        host = args.host
        port = 8086
    user = 'int'
    password = 'gn4intp4'
    dbname = args.database

    client = InfluxDBClient(host=host, port=port, database=dbname)
    logger.info("Influx client ping response: %s" % client.ping())
    return client

def start_udp_server(args):
    bufferSize = 65565
    port = args.int_port
    
    # Start influx database and collector
    influx = influx_client(args)
    collector = IntCollector(influx, args.period)

    # Create a datagram socket
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 8192))
    logger.info("UDP server up and listening at UDP port: %d" % port)

    # Listen for incoming datagrams
    while True:
        message, address = sock.recvfrom(bufferSize)
        logger.info("Received INT report (%d bytes) from: %s" % (len(message), str(address)))
        try:
            # When a packet is received, a report is created and then added to the collector
            report = unpack_int_report(message, str(address[0]))
            if report:
                collector.add_report(report)
        except Exception as e:
            logger.exception("Exception during handling the INT report")

def parse_params():
    parser = argparse.ArgumentParser(description='InfluxBD INTCollector client.')

    parser.add_argument("-i", "--int_port", default=8192, type=int,
        help="Destination port of INT Telemetry reports")

    parser.add_argument("-H", "--host", default="localhost",
        help="InfluxDB server address")

    parser.add_argument("-D", "--database", default="int_telemetry_db",
        help="Database name")

    parser.add_argument("-p", "--period", default=1, type=int,
        help="Time period to push data in normal condition")

    parser.add_argument("-d", "--debug_mode", default=0, type=int,
        help="Set to 1 to print debug information")
    
    parser.add_argument("-c", "--count", default=8, type=int,
        help="Minimum number of packets collected to send to the database")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_params()

    if args.debug_mode > 0:
        logger.setLevel(logging.DEBUG)
    start_udp_server(args)
