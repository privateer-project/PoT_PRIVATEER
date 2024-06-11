import argparse
import time
import socket
import struct
import binascii
import pprint
import logging
from copy import copy
import io
from influxdb import InfluxDBClient


# Log configuration
log_format = "[%(asctime)s] [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format, filename="logs/int_collector.log")
logger = logging.getLogger('int_collector')

first=True
current_timestamp = 0


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
            current_timestamp = int(time.time()*1e3)
        else: 
            self.timestamp = int(time.time()*1e3) - current_timestamp

        logger.debug(vars(self))
        
class IntCollector():
    
    def __init__(self, influx, period):
        self.influx = influx
        self.reports = [] # list of reports
        self.period = period # maximum time delay of int report sending to influx
        self.last_send = time.time() # last time when reports were send to influx
        
        
    def add_report(self, report):
        self.reports.append(report)
        
        reports_cnt = len(self.reports)
        logger.debug('%d reports ready to sent' % reports_cnt)
        # send if several reports are ready to send or some time passed from last sending
        if reports_cnt > (2*args.count - 1):
            logger.info("Sending %d reports to influx from last %s secs" % (reports_cnt, time.time() - self.last_send))
            self.__send_reports()
            self.last_send = time.time()
            
    def __prepare_reports(self, report):
        reports = []
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
        reports.append(json_report)
        return reports
        
        
    def __send_reports(self):
        json_body = []
        
        for report in self.reports:
            json_body.extend(self.__prepare_reports(report))
        logger.info("Json body for influx:\n %s" % pprint.pformat(json_body))
        if json_body:
            try:
                self.influx.write_points(json_body)
                self.last_send = time.time()
                logger.info(" %d int reports sent to the influx" % len(json_body))
            except Exception as e:
                logger.exception(e)
        self.reports = [] # clear reports sent

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
    bufferSize  = 65565
    port = args.int_port
    
    # Start influx database and collector
    influx = influx_client(args)
    collector = IntCollector(influx, args.period)

    # Create a datagram socket
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 8192))
    logger.info("UDP server up and listening at UDP port: %d" % port)

    # Listen for incoming datagrams
    while(True):
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

"""# Configuración del productor de Kafka
kafka_conf = {'bootstrap.servers': '10.2.1.2:9092'}
kafka_producer = Producer(kafka_conf)

# Añade un argumento para el nombre del topic de Kafka
parser.add_argument("-t", "--topic", default="random_pot_topic-col",
        help="Kafka topic to send messages to")

# En el lugar donde envías mensajes a InfluxDB, también envía a Kafka
# Supongamos que 'message' es el mensaje que estás enviando a InfluxDB
kafka_producer.produce(args.topic, message)
kafka_producer.flush()"""

if __name__ == "__main__":
    args = parse_params()
    if args.debug_mode > 0:
        logger.setLevel(logging.DEBUG)
    start_udp_server(args)