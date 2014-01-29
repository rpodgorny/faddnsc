#!/usr/bin/python3

'''
Freakin' Awesome Dynamic DNS client - GUI version.

Usage:
  faddnsc [options] [-u, --url-prefix=<url-prefix>]...

Options:
  -h, --help  Help.
  --log-level DEBUG | INFO | WARNING | ERROR
              Debug level [default: INFO].
  -d, --domain=<domain>
              Domain to subscribe to.
  --host=<host>
              Hostname to report.
  -i, --interval=<interval>
              Update interval (s).
  -u, --url-prefix=<url-prefix>
              URL prefix.
'''

from version import __version__

import os
import sys
from PySide.QtCore import *
from PySide.QtGui import *
import logging
import time
from cfg import cfg
import docopt

from faddns import *


get_addrs = None  # TODO: ugly


class MyTray(QSystemTrayIcon):
	def __init__(self, app, url_prefix):
		icon = QIcon('faddns.png')
		super().__init__(icon)

		self.app = app
		self.url_prefix = url_prefix

		self.addrs_old = None

		self.setToolTip('faddnsc_gui v%s' % __version__)

		menu = QMenu()
		menu.addAction('Force refresh', self.on_refresh)
		menu.addAction('Exit', self.on_exit)
		self.setContextMenu(menu)

		self.t_last = None
		self.startTimer(100)

		self.show()
	#enddef

	def timerEvent(self, e):
		t = time.monotonic()

		if self.t_last and t - self.t_last < 600:
			return
		#endif

		addrs = get_addrs()
		logging.debug(str(addrs))

		if addrs != self.addrs_old:
			all_ok = True
			for url_prefix in self.url_prefix:
				logging.debug('sending info to %s' % url_prefix)
				if not send_addrs(url_prefix, cfg.host, cfg.domain, __version__, addrs):
					all_ok = False
				#endif
			#endfor

			if all_ok:
				self.addrs_old = addrs
			#endif
		else:
			logging.debug('no change, doing nothing')
		#endif

		self.t_last = t
	#enddef

	def on_refresh(self):
		pass
	#enddef

	def on_exit(self):
		self.app.quit()
	#enddef
#endclass


def logging_setup(level):
	logging.basicConfig(level=level)
#enddef


def main():
	args = docopt.docopt(__doc__, version=__version__)

	log_level = args['--log-level']
	logging_setup(log_level)

	logging.info('*' * 40)
	logging.info('starting faddnsc_gui v%s' % __version__)

	logging.debug(str(args))

	for fn in (os.path.expanduser('~/.faddnsc.conf'), 'faddnsc.ini', '/etc/faddnsc.conf'):
		if not os.path.isfile(fn): continue
		logging.info('reading configuration from %s' % fn)
		cfg.read_from_ini(fn)
		break
	#endfor

	if args['--domain']: cfg.domain = args['--domain']
	if args['--host']: cfg.host = args['--host']
	if args['--interval']: cfg.interval = float(args['--interval'])
	if args['--url-prefix']: cfg.url_prefix = args['--url-prefix']

	err = cfg.check()
	if err:
		logging.critical(err)
		return
	#endif

	logging.info('%s' % cfg)

	global get_addrs
	if sys.platform == 'win32':
		logging.info('detected win32')
		get_addrs = get_addrs_windows
	elif sys.platform.startswith('linux'):
		logging.info('detected linux')
		get_addrs = get_addrs_linux
	else:
		logging.critical('unknown platform! (%s)' % sys.platform)
		return
	#endif

	app = QApplication(sys.argv[1:])

	tray = MyTray(app, cfg.url_prefix)

	app.exec_()

	logging.info('done')
#enddef


if __name__ == '__main__':
	main()
#endif
