#!/usr/bin/env python
import os.path
import re
from setuptools import Command, find_packages, setup

class PyTest(Command):
	user_options = []
	def initialize_options(self):
		pass
	def finalize_options(self):
		pass
	def run(self):
		import sys,subprocess
		errno = subprocess.call([sys.executable, "test.sh"])
		raise SystemExit(errno)

def parse_requirements(file_name):
	"""Taken from http://cburgmer.posterous.com/pip-requirementstxt-and-setuppy"""
	requirements = []
	for line in open(os.path.join(os.path.dirname(__file__), "config", file_name), "r"):
		line = line.strip()
		# comments and blank lines
		if re.match(r"(^#)|(^$)", line):
			continue
		requirements.append(line)
	return requirements

setup(
	name="techbot",
	version="0.9.0",
	url = "https://wiki.knewton.net/index.php/Tech",
	author="Devon Jones",
	author_email="devon@knewton.com",
	license = "GPLv3",
	packages=find_packages(),
	scripts = ["bin/techbot"],
	cmdclass = {"test": PyTest},
	package_data = {"config": ["requirements*.txt"]},
	install_requires=parse_requirements("requirements.txt"),
	tests_require=parse_requirements("requirements.testing.txt"),
	description = "Knewton's chat bot.",
)
