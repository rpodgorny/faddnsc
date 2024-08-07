import ipaddress
import logging
import subprocess
import sys
import time
import urllib
import urllib.error
import urllib.parse
import urllib.request


# TODO: get rid of this dependency
if sys.platform == "win32":
    import netifaces


def logging_setup(level, fn=None):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(levelname)s: %(message)s")
    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    if fn:
        formatter = logging.Formatter("%(asctime)s: %(levelname)s: %(message)s")
        fh = logging.FileHandler(fn)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)


def call_OLD(cmd):
    logging.debug(f"calling: {cmd}")

    import os

    f = os.popen(cmd)
    ret = f.read()
    f.close()
    return ret


def call(cmd):
    logging.debug(f"calling: {cmd}")
    return subprocess.check_output(cmd, shell=True).decode("cp1250")


def get_addrs_windows():
    ret = {}

    # TODO: this is the only way i know to list ipv4 addresses :-(
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface)
        for addr in addrs:
            if netifaces.AF_INET not in addrs:
                continue
            for addr in addrs[netifaces.AF_INET]:
                a = addr["addr"]
                if "inet" not in ret:
                    ret["inet"] = set()
                ret["inet"].add(a)

    lines = call("netsh interface ipv6 show address")

    for line in lines.split("\n"):
        if "Temporary" in line:
            continue

        for word in line.split():
            word = word.strip().lower()

            # TODO: hackish but works
            try:
                a = ipaddress.IPv6Address(word)
            except:
                continue

            ###if not ':' in word: continue
            ###if not word.startswith('200'): continue

            if "inet6" not in ret:
                ret["inet6"] = set()
            ret["inet6"].add(word)

    # disable ether for now
    """
	lines = call('ipconfig /all')
	for word in lines.split():
		word = word.strip().lower()
		###if not re.match('..-..-..-..-..-..', word): continue

		word = word.replace('-', ':')

		if not 'ether' in ret: ret['ether'] = set()
		ret['ether'].add(word)
	"""

    # TODO: this is the only way i know to list ethernet addresses :-(
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface)
        for addr in addrs:
            if -1000 not in addrs:
                continue
            for addr in addrs[-1000]:
                a = addr["addr"]
                if not a:
                    continue
                if "ether" not in ret:
                    ret["ether"] = set()
                ret["ether"].add(a)

    return ret


def get_addrs_linux():
    ret = {}

    lines = call("ip addr").split("\n")

    for line in lines:
        line = line.strip()

        if "ether" not in line and "inet" not in line:
            continue

        if "temporary" in line:
            continue

        addr_type, addr, _ = line.split(" ", 2)
        addr_type = addr_type.lower()
        addr = addr.lower()

        if "ether" in addr_type:
            addr_type = "ether"
        elif "inet6" in addr_type:
            addr_type = "inet6"
        elif "inet" in addr_type:
            addr_type = "inet"
        else:
            logging.error(f"unknown address type! ({addr_type})")

        try:
            addr = addr.split("/")[0]
        except Exception:
            pass

        if addr_type not in ret:
            ret[addr_type] = set()
        ret[addr_type].add(addr)

    return ret


def send_addrs(url, host, version, addrs):
    logging.debug(f"sending info to {url}")

    d = {
        "version": version,
        "host": host,
        #'records': recs
    }
    d.update(addrs)
    url_params = urllib.parse.urlencode(d, True)
    url = f"{url}?{url_params}"

    logging.debug(url)

    try:
        u = urllib.request.urlopen(url).read().decode("utf-8")
    except urllib.error.URLError as e:
        # logging.exception('urllib.request.urlopen() exception, probably failed to connect')
        logging.error(f"failed with: {str(e)}")
        return False

    if "OK" in "".join(u):
        logging.debug("OK")
        return True
    else:
        logging.warning(f"did not get OK, server returned: {u}")

    return False


class MainLoop:
    def __init__(self, get_addrs_f, host, url, version, interval):
        self.get_addrs_f = get_addrs_f
        self.host = host
        self.url = url
        self.version = version
        self.interval = interval

        self._run = False
        self._refresh = False

    def run(self):
        logging.debug("main loop")

        # addrs_old = None

        interval = 60  # TODO: hard-coded shit
        t_last = 0
        self._run = True
        while self._run:
            t = time.monotonic()

            if t - t_last > interval or self._refresh:
                addrs = self.get_addrs_f()
                logging.debug(str(addrs))

                if not addrs:
                    logging.debug("no addresses, setting interval to 60")
                    interval = 60  # TODO: hard-coded shit
                else:
                    logging.debug(f"some addresses, setting interval to {self.interval}")
                    interval = self.interval

                # disable this for now since we also want to use this as 'i am alive' signal
                # if self._refresh or addrs != addrs_old:
                if 1:
                    logging.info(f"sending info to {self.url} ({addrs})")
                    res = send_addrs(self.url, self.host, self.version, addrs)
                    if res:
                        # addrs_old = addrs
                        pass
                    else:
                        logging.warning("send_addrs failed")
                else:
                    logging.debug("no change, doing nothing")

                self._refresh = False
                t_last = t
            else:
                time.sleep(0.1)

        logging.debug("exited main loop")

    def stop(self):
        self._run = False

    def refresh(self):
        self._refresh = True
