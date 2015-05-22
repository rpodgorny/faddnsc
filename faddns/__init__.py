#!/usr/bin/python3

import sys
import urllib
import urllib.request
import urllib.error
import urllib.parse
import ipaddress
import logging
import subprocess
import re
import time

# TODO: get rid of this dependency
if sys.platform == 'win32':
	import netifaces
#endif


def logging_setup(level, fn=None):
	logger = logging.getLogger()
	logger.setLevel(logging.DEBUG)

	formatter = logging.Formatter('%(levelname)s: %(message)s')
	sh = logging.StreamHandler()
	sh.setLevel(level)
	sh.setFormatter(formatter)
	logger.addHandler(sh)

	if fn:
		formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s')
		fh = logging.FileHandler(fn)
		fh.setLevel(level)
		fh.setFormatter(formatter)
		logger.addHandler(fh)
	#endif
#enddef


def call_OLD(cmd):
	logging.debug('calling: %s' % cmd)

	import os
	f = os.popen(cmd)
	ret = f.read()
	f.close()
	return ret
#enddef


def call(cmd):
	logging.debug('calling: %s' % cmd)
	return subprocess.check_output(cmd, shell=True).decode('cp1250')
#enddef


def get_addrs_windows():
	ret = {}

	# TODO: this is the only way i know to list ipv4 addresses :-(
	for interface in netifaces.interfaces():
		addrs = netifaces.ifaddresses(interface)
		for addr in addrs:
			if not netifaces.AF_INET in addrs: continue
			for addr in addrs[netifaces.AF_INET]:
				a = addr['addr']
				if not 'inet' in ret: ret['inet'] = set()
				ret['inet'].add(a)
			#endfor
		#endfor
	#endfor

	lines = call('netsh interface ipv6 show address')

	for line in lines.split('\n'):
		if 'Temporary' in line: continue

		for word in line.split():
			word = word.strip().lower()

			# TODO: hackish but works
			try:
				a = ipaddress.IPv6Address(word)
			except:
				continue
			#endtry

			###if not ':' in word: continue
			###if not word.startswith('200'): continue

			if not 'inet6' in ret: ret['inet6'] = set()
			ret['inet6'].add(word)
		#endfor
	#endfor

	# disable ether for now
	'''
	lines = call('ipconfig /all')
	for word in lines.split():
		word = word.strip().lower()
		###if not re.match('..-..-..-..-..-..', word): continue

		word = word.replace('-', ':')

		if not 'ether' in ret: ret['ether'] = set()
		ret['ether'].add(word)
	#endfor
	'''

	# TODO: this is the only way i know to list ethernet addresses :-(
	for interface in netifaces.interfaces():
		addrs = netifaces.ifaddresses(interface)
		for addr in addrs:
			if not -1000 in addrs: continue
			for addr in addrs[-1000]:
				a = addr['addr']
				if not a: continue
				if not 'ether' in ret: ret['ether'] = set()
				ret['ether'].add(a)
			#endfor
		#endfor
	#endfor

	return ret
#enddef


def get_addrs_linux():
	ret = {}

	lines = call('ip addr').split('\n')

	for line in lines:
		line = line.strip()

		if not 'ether' in line \
		and not 'inet' in line:
			continue
		#endif

		if 'temporary' in line: continue

		addr_type, addr, _ = line.split(' ', 2)
		addr_type = addr_type.lower()
		addr = addr.lower()

		if 'ether' in addr_type:
			addr_type = 'ether'
		elif 'inet6' in addr_type:
			addr_type = 'inet6'
		elif 'inet' in addr_type:
			addr_type = 'inet'
		else:
			logging.error('unknown address type! (%s)' % addr_type)
		#endif

		try:
			addr = addr.split('/')[0]
		except: pass

		'''
		if addr_type == 'ether':
			if addr == '00:00:00:00:00:00': continue
		elif addr_type == 'inet':
			if ipaddress.ip_address(addr).is_private: continue
			if ipaddress.ip_address(addr).is_loopback: continue
			if ipaddress.ip_address(addr).is_link_local: continue
		elif addr_type == 'inet6':
			if ipaddress.ip_address(addr).is_private: continue
			if ipaddress.ip_address(addr).is_loopback: continue
			if ipaddress.ip_address(addr).is_link_local: continue
		#endif
		'''

		if not addr_type in ret: ret[addr_type] = set()
		ret[addr_type].add(addr)
	#endfor

	'''
	# disable ether for now
	if 'ether' in ret:
		del ret['ether']
	#endif
	'''

	return ret
#enddef


def send_addrs(url, host, version, addrs):
	# TODO: for the next version?
	#recs = []
	#for i in addrs:
	#	r = []
	#	for k,v in i.items(): r.append('%s=%s' % (k, v))
	#	r = ','.join(r)
	#	recs.append(r)
	#endfor
	#logging.debug('recs = %s' % recs)

	logging.debug('sending info to %s' % url)

	d = {
		'version': version,
		'host': host,
		#'records': recs
	}
	d.update(addrs)
	url = '%s?%s' % (url, urllib.parse.urlencode(d, True))

	logging.debug(url)

	try:
		u = urllib.request.urlopen(url).read().decode('utf-8')
	except urllib.error.URLError as e:
		#logging.exception('urllib.request.urlopen() exception, probably failed to connect')
		logging.error('failed with: %s' % str(e))
		return False
	#endtry

	if 'OK' in ''.join(u):
		logging.debug('OK')
		return True
	else:
		logging.warning('did not get OK, server returned: %s' % u)
	#endif

	return False
#enddef


class MainLoop:
	def __init__(self, get_addrs_f, host, url, version, interval):
		self.get_addrs_f = get_addrs_f
		self.host = host
		self.url = url
		self.version = version
		self.interval = interval

		self._run = False
		self._refresh = False
	#enddef

	def run(self):
		logging.debug('main loop')

		addrs_old = None

		interval = 60  # TODO: hard-coded shit
		t_last = 0
		self._run = True
		while self._run:
			t = time.monotonic()

			if t - t_last > interval or self._refresh:
				addrs = self.get_addrs_f()
				logging.debug(str(addrs))

				if not addrs:
					logging.debug('no addresses, setting interval to 60')
					interval = 60  # TODO: hard-coded shit
				else:
					logging.debug('some addresses, setting interval to %s' % self.interval)
					interval = self.interval
				#endif

				# disable this for now since we also want to use this as 'i am alive' signal
				#if self._refresh or addrs != addrs_old:
				if 1:
					logging.info('sending info to %s (%s)' % (self.url, addrs))
					if send_addrs(self.url, self.host, self.version, addrs):
						addrs_old = addrs
					else:
						logging.warning('send_addrs failed')
					#endif
				else:
					logging.debug('no change, doing nothing')
				#endif

				self._refresh = False
				t_last = t
			else:
				time.sleep(0.1)
			#endif
		#endwhile

		logging.debug('exited main loop')
	#enddef

	def stop(self):
		self._run = False
	#enddef

	def refresh(self):
		self._refresh = True
	#enddef
#endclass
