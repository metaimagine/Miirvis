#!/usr/bin/env python3
from aiohttp import ClientSession
import asyncio
import logging
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.miservice.miaccount import MiAccount
from app.miservice.miiocommand import miio_command_help, miio_command
from app.miservice.miioservice import MiIOService
from app.miservice.minaservice import MiNAService

load_dotenv()
MISERVICE_VERSION = '2.0.1'

logger = logging.getLogger(__name__)


def usage():
    print("MiService %s - XiaoMi Cloud Service\n" % MISERVICE_VERSION)
    print("Usage: The following variables must be set:")
    print("           export MI_USER=<Username>")
    print("           export MI_PASS=<Password>")
    print("           export MI_DID=<Device ID|Name>\n")
    print(miio_command_help(prefix=sys.argv[0] + ' '))


async def main(args):
    try:
        async with ClientSession() as session:
            env = os.environ
            account = MiAccount(session, env.get('MI_USER'), env.get('MI_PASS'),
                                os.path.join(str(Path.home()), '.mi.token'))
            if args.startswith('mina'):
                service = MiNAService(account)
                result = await service.device_list()
                if len(args) > 4:
                    await service.send_message(result, -1, args[4:])
            else:
                service = MiIOService(account)
                print("===============")
                print(service, env.get('MI_DID'), args, sys.argv[0])
                print("===============")

                result = await miio_command(service, env.get('MI_DID'), args)
            if not isinstance(result, str):
                result = json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.exception(e)
    print(result)


if __name__ == '__main__':
    argv = sys.argv
    argc = len(argv)
    if argc > 1 and argv[1].startswith('-v'):
        argi = 2
        index = int(argv[1][2]) if len(argv[1]) > 2 else 4
        level = [logging.NOTSET, logging.FATAL, logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG][index]
    else:
        argi = 1
        level = logging.WARNING
    if argc > argi:
        if level != logging.NOTSET:
            _LOGGER = logging.getLogger('miservice')
            _LOGGER.setLevel(level)
            _LOGGER.addHandler(logging.StreamHandler())
        asyncio.run(main(' '.join(argv[argi:])))
    else:
        usage()
