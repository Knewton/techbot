import yaml
import os
import os.path
import sqlite3dbm

CONFIG_DIR = os.path.expanduser("~/.techbot")
CONFIG = os.path.expanduser("~/.techbot/techbot.yml")
DB = os.path.expanduser("~/.techbot/techbot.db")

def get_config(options):
	create_dir()
	if os.path.exists(CONFIG):
		stream = file(CONFIG, 'r')
		config = yaml.load(stream)
		if not options.jid:
			options.jid = config['jid']
		if not options.password:
			options.password = config['password']
		if not options.hostname:
			options.hostname = config['hostname']
		if options.debug == None:
			options.debug = config['debug']
	else:
		generate_config(options)

def generate_config(options):
	if not os.path.exists(CONFIG):
		config = {
			'jid': options.jid,
			'password': options.password,
			'hostname': options.hostname,
			'debug': options.debug
		}
		stream = file(CONFIG, 'w')
		yaml.dump(config, stream)

def get_db():
	create_dir()
	db = sqlite3dbm.sshelve.open(DB)
	return db

def create_dir():
	if not os.path.exists(CONFIG_DIR):
		os.mkdir(CONFIG_DIR)
