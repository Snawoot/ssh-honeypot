# ssh-honeypot

Special task SSH honeypot. Collects used SSH passwords and issued commands into SQLite3 database (`-D`). All unknown commands answered with banner from specified text file (`-B`).

Initially server does not accepts any login and password, but with every attempt there is preconfigured probability (`-P`) of accepting password and granting login. Accepted login-password pairs stored into database and considered valid for some time (`-T`). All public key authorizations are accepted.

Each session logged into database and daemon output.

## System Requirements

* Python 3.5.3+
* sqlite3 3.24.0+ (on Debian 9 use command `apt install -t stretch-backports sqlite3`)

## Install

`pip3 install -U https://github.com/Snawoot/ssh-honeypot/archive/master.zip`

Also you may install application into virtual env if you like.

## Running

You have to generate SSH server keys first. You may use `make keys` Makefile target from project directory.

### Synopsis

```
$ ssh-honeypot --help
usage: ssh-honeypot [-h] [-v {debug,info,warn,error,fatal}] -D USER_DATABASE
                    [-T USER_TTL] [-b BIND [BIND ...]] -B BANNER_FILE -k
                    HOST_KEY [HOST_KEY ...] [-P LOGIN_PROBABILITY]

Special task SSH honeypot

optional arguments:
  -h, --help            show this help message and exit
  -v {debug,info,warn,error,fatal}, --verbosity {debug,info,warn,error,fatal}
                        logging verbosity (default: info)
  -D USER_DATABASE, --user-database USER_DATABASE
                        user database file (default: None)
  -T USER_TTL, --user-ttl USER_TTL
                        user account Time To Live in seconds (default: 604800)

listen options:
  -b BIND [BIND ...], --bind BIND [BIND ...]
                        bind address and port (separated with #) (default:
                        ['127.0.0.1#8022'])
  -B BANNER_FILE, --banner-file BANNER_FILE
                        text file with banner template (default: None)
  -k HOST_KEY [HOST_KEY ...], --host-key HOST_KEY [HOST_KEY ...]
                        host key files (default: None)
  -P LOGIN_PROBABILITY, --login-probability LOGIN_PROBABILITY
                        desired probability of login success (default:
                        0.1329459110265233)
```

### Example

```bash
ssh-honeypot -v info -B /var/lib/ssh-honeypot/message.txt -k /var/lib/ssh-honeypot/ssh_dsa_host_key /var/lib/ssh-honeypot/ssh_ecdsa_host_key /var/lib/ssh-honeypot/ssh_rsa_host_key -D /var/lib/ssh-honeypot/ssh_users -b '::#22' '0.0.0.0#22' -P 0.2
```
