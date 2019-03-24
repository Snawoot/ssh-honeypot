#!/usr/bin/env python3

import argparse
import asyncio
import signal
import logging
from functools import partial

from .server import HoneypotServer
from .constants import LogLevel
from .utils import setup_logger


def parse_args():

    def check_port(value):
        ivalue = int(value)
        if not 0 < ivalue < 65536:
            raise argparse.ArgumentTypeError(
                "%s is not a valid port number" % value)
        return ivalue

    def check_probability_float(value):
        fvalue = float(value)
        if not (0 <= fvalue <= 1):
            raise argparse.ArgumentTypeError(
                "%s is not a valid probability" % value)
        return fvalue

    def check_positive_int(value):
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                "%s is not a valid positive integer" % value)
        return fvalue

    parser = argparse.ArgumentParser(
        description="Special task SSH honeypot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-v", "--verbosity",
                        help="logging verbosity",
                        type=LogLevel.__getitem__,
                        choices=list(LogLevel),
                        default=LogLevel.info)
    parser.add_argument("-D", "--user-database",
                        required=True,
                        help="user database file")
    parser.add_argument("-T", "--user-ttl",
                        type=check_positive_int,
                        default=7*24*3600,
                        help="user account Time To Live in seconds")

    listen_group = parser.add_argument_group('listen options')
    listen_group.add_argument("-b", "--bind",
                              nargs="+",
                              default=["127.0.0.1#8022"],
                              help="bind address and port (separated with #)")

    payload_group = parser.add_argument_group('payload options')
    listen_group.add_argument("-B", "--banner-file",
                              required=True,
                              help="text file with banner template")
    listen_group.add_argument("-k", "--host-key",
                              nargs='+',
                              required=True,
                              help="host key files")
    listen_group.add_argument("-P", "--login-probability",
                              default=0.1329459110265233,
                              type=check_probability_float,
                              help="desired probability of login success")
    return parser.parse_args()


def exit_handler(exit_event, signum, frame):
    logger = logging.getLogger('MAIN')
    if exit_event.is_set():
        logger.warning("Got second exit signal! Terminating hard.")
        os._exit(1)
    else:
        logger.warning("Got first exit signal! Terminating gracefully.")
        exit_event.set()


async def heartbeat():
    while True:
        await asyncio.sleep(.5)


async def amain(args, loop):
    logger = logging.getLogger('MAIN')
    with open(args.banner_file, encoding='ascii') as f:
        banner = f.read()
    bind_pairs = ((p[0], int(p[1])) for p in
        (b.partition('#')[::2] for b in args.bind))
    server = HoneypotServer(bind=bind_pairs,
                            banner=banner,
                            keys=args.host_key,
                            probability=args.login_probability,
                            db_file=args.user_database,
                            user_ttl=args.user_ttl,
                            loop=loop)
    logger.debug("Starting server...")
    await server.start()
    logger.info("Server startup completed.")

    exit_event = asyncio.Event(loop=loop)
    beat = asyncio.ensure_future(heartbeat(), loop=loop)
    sig_handler = partial(exit_handler, exit_event)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    await exit_event.wait()
    logger.debug("Eventloop interrupted. Shutting down server...")
    beat.cancel()
    await server.stop()


def main():
    args = parse_args()
    logger = setup_logger('MAIN', args.verbosity)
    setup_logger(HoneypotServer.__name__, args.verbosity)
    setup_logger('UserDatabase', args.verbosity)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain(args, loop))
    loop.close()
    logger.info("Server stopped.")


if __name__ == '__main__':
    main()
