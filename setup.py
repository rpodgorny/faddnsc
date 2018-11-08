from setuptools import setup, find_packages

from faddns.version import __version__

setup(
	name = 'faddns',
	version = __version__,
	options = {
		'build_exe': {
			'compressed': True,
			'include_files': ['etc/faddnsc.conf', ]
		},
	},
	scripts = ['faddnsc', ],
	packages = find_packages(),
)
