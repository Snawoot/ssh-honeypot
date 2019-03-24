import asyncio
import socket
import weakref
import random
import logging
import string
import time
import uuid
import bashlex
import datetime

import asyncssh

from .database import UserDatabase


class ExitCommand(Exception):
    pass


class HoneypotServer(asyncssh.SSHServer):
    hostname = "localhost"
    motd = """Linux mx 4.19.0-0.bpo.2-amd64 #1 SMP Debian 4.19.16-1~bpo9+1 (2019-02-07) x86_64

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
"""

    def __init__(self, *,
                 bind,
                 keys,
                 banner,
                 probability,
                 db_file,
                 user_ttl,
                 loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._bind = bind
        self._banner = string.Template(banner)
        self._keys = keys
        self._probability = probability
        self._db = UserDatabase(db_file)
        self._user_ttl = user_ttl
        self._children = weakref.WeakSet()

    def connection_made(self, conn):
        self._logger.info('SSH connection received from %s.',
                          conn.get_extra_info('peername')[0])

    def connection_lost(self, exc):
        if exc:
            self._logger.error('SSH connection error: ' + str(exc))
        else:
            self._logger.info('SSH connection closed.')

    def begin_auth(self, username):
        return True

    def password_auth_supported(self):
        return True

    def public_key_auth_supported(self):
        return True

    def validate_public_key(self, username, key):
        self._logger.warning('Attempt: username = %s, key = %s',
                             repr(username), repr(key.get_fingerprint()))
        return True

    async def validate_password(self, username, password):
        self._logger.info('Attempt: username = %s, password = %s',
                          repr(username), repr(password))
        await self._db.count_credentials(username, password)
        user_record = await self._db.check_user(username, password)
        if user_record is not None and ((time.time() - user_record[0]) < self._user_ttl):
            self._logger.debug('Found user %s in DB', repr(username))
            return True
        else:
            if random.random() < self._probability:
                self._logger.info('Creating new user %s.', (username, password))
                await self._db.add_user(username, password)
                return True
            else:
                self._logger.debug('User %s failed to authenticate itself.',
                                   (username, password))
                return False

    async def handler(self, process):
        session = uuid.uuid4()
        username = process.get_extra_info('username')
        interactive = process.get_terminal_type() is not None
        if interactive:
            prompt = "%s@%s:~%s " % (username, self.hostname,
                                     "#" if username == "root" else "$")
        else:
            prompt = ""
        self._logger.warn('Got user login: user %s from %s',
                          repr(username),
                          process.get_extra_info('peername'))
        if process.command is not None:
            try:
                await self.process_command(session, process, process.command, True)
            except ExitCommand:
                pass
        else:
            if interactive:
                process.stderr.write(self.motd)
            process.stderr.write(prompt)
            while not process.stdin.at_eof():
                try:
                    line = await process.stdin.readline()
                except asyncssh.TerminalSizeChanged:
                    continue
                except asyncssh.BreakReceived:
                    if interactive:
                        process.stderr.write("^C\n")
                        process.stderr.write(prompt)
                    else:
                        break
                else:
                    if not line:
                        process.stderr.write('\n')
                        break
                    line = line.rstrip('\n')
                    if not line:
                        process.stderr.write(prompt)
                        continue
                    try:
                        await self.process_command(session, process, line, False)
                    except ExitCommand:
                        break
                    else:
                        process.stderr.write(prompt)
        process.exit(0)

    async def process_command(self, session, process, cmdline, only=True):
        ts = time.time()
        username = process.get_extra_info('username')
        try:
            await self._db.log_command(username, session, ts, cmdline, only)
        except Exception as e:
            self._logger.exception("Command log failed: %s", e)
        self._logger.info("ts=%.3f. session=%s, user=%s, command=%s, only=%s",
                          ts, session.hex, repr(username), repr(cmdline), only)
        try:
            firstcmd = next(bashlex.split(cmdline))
        except StopIteration:
            pass
        except:
            process.stderr.write("bash: syntax error near unexpected token "
                                 "`%s'" % cmdline)
        else:
            if firstcmd == 'exit':
                process.stderr.write("logout\n\n")
                raise ExitCommand()
            elif firstcmd == 'uname':
                process.stdout.write('Linux localhost 4.19.0-0.bpo.2-amd64 #1 '
                                     'SMP Debian 4.19.16-1~bpo9+1 (2019-02-07)'
                                     ' x86_64 GNU/Linux\n')
            elif firstcmd == 'uptime':
                date = datetime.datetime.utcnow().strftime("%H:%M:%S")
                process.stdout.write(" %s up 5 days,  2:48,  1 user,  "
                                     "load average: 0.00, 0.00, 0.00\n" % date)
            elif firstcmd == 'date':
                date = datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")
                process.stdout.write(date + '\n')
            elif firstcmd == 'whoami':
                process.stdout.write(username + '\n')
            else:
                message = self._banner.safe_substitute(username=username, cmdline=cmdline)
                process.stderr.write(message)

    async def stop(self):
        for server in self._servers:
            server.close()
        await asyncio.wait([s.wait_closed() for s in self._servers])
        if self._children:
            self._logger.debug("Cancelling %d client handlers...",
                               len(self._children))
            for task in self._children:
                task.cancel()
            await asyncio.wait(self._children)

    async def start(self):
        def _spawn(process):
            self._children.add(
                self._loop.create_task(self.handler(process)))

        await self._db.prepare()
        fabric = lambda: self
        start_tasks = [asyncssh.create_server(fabric,
                                              b[0], b[1],
                                              server_host_keys=self._keys,
                                              server_version='OpenSSH_7.4p1 Debian-10+deb9u6',
                                              reuse_address=True,
                                              reuse_port=True,
                                              process_factory=_spawn)
                       for b in self._bind]
        done, pending = await asyncio.wait(start_tasks)
        self._servers = [t.result() for t in done]
        self._logger.info("Server ready.")
