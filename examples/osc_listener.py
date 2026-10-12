import argparse
import math
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

def print_handler(address, *args):
    print(f"[OSC] {address}: {args}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1", help="The ip to listen on")
    parser.add_argument("--port", type=int, default=9000, help="The port to listen on")
    args = parser.parse_args()

    dispatcher = Dispatcher()
    dispatcher.map("/wall/*", print_handler)
    
    server = BlockingOSCUDPServer((args.ip, args.port), dispatcher)
    print(f"Listening for Lidar Wall OSC messages on {args.ip}:{args.port}")
    server.serve_forever()
