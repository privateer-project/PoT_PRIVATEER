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
from influxdb import InfluxDBClient
from confluent_kafka import Producer

# Log configuration
log_format = "[%(asctime)s] [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format, filename="logs/int_collector.log")
logger = logging.getLogger('int_collector')

first = True
current_timestamp = 0

# Kafka configuration
kafka_conf = {'bootstrap.servers': '10.2.1.3:9092'}
kafka_producer = Producer(kafka_conf)
kafka_topic = "PoT-tests"

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
            
    def _prepare_reports(self, report):
        # Report structure
        json_report = {
            "measurement": "int_telemetry",
            'time': report.timestamp,
            "fields": {
                "Switch IP": report.address,
                "Service Path Identifier": report.service_path_identifier,
                "Service Index": report.service_index,
                "RND": report.rnd,
                "CML": report.cml,
                "Sequence Number": report.seq_number,
                "Dropped": report.dropped
            }
        }
        return json_report
        
    def _send_reports(self):
        json_body = []
        kafka_reports = []
        for report in self.reports:
            json_report = self._prepare_reports(report)
            json_body.append(json_report)
            kafka_reports.append(json.dumps(json_report))

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
