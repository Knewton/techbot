#!/usr/bin/env python
import subprocess
import xmpp
import random
import inspect
import re
from threading import RLock
from jabberbot import JabberBot, botcmd
from config import get_db

def contentcmd(*args, **kwargs):
	"""Decorator for bot commentary"""

	def decorate(func, name=None):
		setattr(func, '_jabberbot_content_command', True)
		setattr(func, '_jabberbot_command_name', name or func.__name__)
		return func

	if len(args):
		return decorate(args[0], **kwargs)
	else:
		return lambda func: decorate(func, **kwargs)

class TechBot(JabberBot):
	def __init__(self, username, password, **kwargs):
		JabberBot.__init__(self, username, password, **kwargs)
		self.PING_FREQUENCY = 60
		self.content_commands = {}
		self.add_content_commands()
		self.db = get_db()
		self.rlock = RLock()
		self.last_message = {}

	def add_content_commands(self):
		for name, value in inspect.getmembers(self, inspect.ismethod):
			if getattr(value, '_jabberbot_content_command', False):
				name = getattr(value, '_jabberbot_command_name')
				self.log.info('Registered content command: %s' % name)
				self.content_commands[name] = value

	@botcmd(hidden=True)
	def sub(self, mess, args, **kwargs):
		tokens = mess.getBody().split(' ')
		if len(tokens) < 2:
			return ' '.join([
				"You must include the name of the resource to",
				"subscribe to"])
		roster = self.conn.Roster.getRoster()
		roster.Subscribe(xmpp.JID(tokens[1]))
		return "Subscribed: %s" % tokens[1]

	@botcmd(hidden=True)
	def unsub(self, mess, args, **kwargs):
		tokens = mess.getBody().split(' ')
		if len(tokens) < 2:
			return ' '.join([
				"You must include the name of the resource to",
				"unsubscribe from"])
		roster = self.conn.Roster.getRoster()
		for item in roster.getItems():
			if tokens[1] == item:
				roster.Unsubscribe(xmpp.JID(item))
				return "Unsubscribed: %s" % item
		return "%s not in roster" % tokens[1]

	@botcmd(hidden=True)
	def ceiling(self, mess, args, **kwargs):
		tokens = mess.getBody().split(' ')
		if len(tokens) < 2:
			return ' '.join([
				"You must include a room name you are asking to be invited to.",
				"Call .rooms for a list"])
		room = tokens[1]
		try:
			roomjid = self.get_room_jid(room)
			body = "/me %s" %(' '.join(tokens[2:]))
			self.send(roomjid, body)
			return "sent"
		except Exception, e:
			return str(e)

	@botcmd
	def uptime(self, mess, args, alias, **kwargs):
		"""Get current uptime information"""
		body = subprocess.check_output('uptime')
		return self.send_to_subscriber(alias, mess, body)

	@botcmd
	def rooms(self, mess, args, alias, **kwargs):
		"""Ask TechBot for a room list"""
		rooms = self.get_rooms()
		message = []
		for room in rooms:
			message.append(room.getNode())
		message.sort()
		message.insert(0, "TechBot manages the following rooms:")
		return self.send_to_subscriber(alias, mess, '\n'.join(message))

	@botcmd
	def invite(self, mess, args, **kwargs):
		"""
		Ask TechBot to invite you to a room
		Format: .invite <room name>
		"""
		if self.is_room(mess):
			return "Send .invite requests directly to techbot@knewton.com"
		tokens = mess.getBody().split(' ')
		if len(tokens) < 2:
			return ' '.join([
				"You must include a room name you are asking to be invited to.",
				"Call .rooms for a list"])
		room = tokens[1]
		roomjids = self.get_rooms()
		rooms = [r.getNode() for r in roomjids]
		if room not in rooms:
			return ' '.join([
				"%s is not a room that I'm aware of." % room,
				"Call .rooms for a list"])
		for jid in roomjids:
			if jid.getNode() == room:
				body = "/invite %s@%s" %(
					mess.getFrom().getNode(),
					mess.getFrom().getDomain())
				self.send(jid, body)
				return "You have been invited to %s" % room
		raise Exception("This should be unreachable")

	@botcmd
	def hype(self, mess, args, **kwargs):
		"""
		Ask TechBot to get some hype up into this room.  Sick.
		Format: .hype (From inside a room)
		        .hype <roomname> directly to techbot
		"""
		if self.is_room(mess):
			return select_hype()
		else:
			tokens = mess.getBody().split(' ')
			if len(tokens) < 2:
				return ' '.join([
					"You must include a room name you are asking to be",
					"invited to. Call .rooms for a list"])
			room = tokens[1]
			try:
				roomjid = self.get_room_jid(room)
				body = select_hype()
				self.send(roomjid, body)
				return "sent"
			except Exception, e:
				return str(e)

	def get_lock_fundamentals(self, mess, alias):
		if self.is_room(mess):
			room = str(mess.getFrom()).split('@')[0]
			owner = self.alias_to_email(alias, str(mess.getFrom()))
			body = mess.getBody()
			tokens = body.split(" ")
			tokens.pop(0) # .lock
			lock = tokens.pop(0)
		else:
			owner = str(mess.getFrom()).split('/')[0]
			body = mess.getBody()
			tokens = body.split(" ")
			tokens.pop(0) # .lock
			room = tokens.pop(0)
			lock = tokens.pop(0)
		return room, owner, lock, ' '.join(tokens)

	def kill_all_humans(self):
		# For future use
		pass

	@botcmd
	def lock(self, mess, args, alias, **kwargs):
		"""
		Establish a lock over a resource.
		Only you can unlock, but anyone can break.
		Calling this will broadcast in the room the lock came from.
		Format: .lock <lockname> (message) From inside a room
		        .lock <roomname> <lockname> (message) directly to techbot
		"""
		room, owner, lock, note = self.get_lock_fundamentals(mess, alias)
		try:
			roomjid = self.get_room_jid(room)
			response = self.set_lock(lock, owner, room, note)
			if self.is_room(mess):
				return response
			else:
				self.send(roomjid, response)
				return response
		except Exception, e:
			return str(e)

	def set_lock(self, lock, owner, room, note):
		with self.rlock:
			locks = self.db.get('locks', {})
			room_locks = locks.setdefault(room, {})
			if room_locks.get(lock):
				elock, eowner, enote = room_locks.get(lock)
				if eowner != owner:
					raise Exception("Lock already held: \n"
						"    %s/%s: %s (%s)" % (room, lock, eowner, enote))
			room_locks[lock] = (lock, owner, note)
			self.db['locks'] = locks
			return "Lock established: \n    %s/%s: %s %s" % (
				room, lock, owner, note)

	@botcmd
	def locks(self, mess, args, alias=None, **kwargs):
		"""
		Get a list of locks
		Format: .locks (print all locks for a room, or if direct, alias for .locks all)
		        .locks all (print all locks)
		        .locks <roomname> (print all locks for a room)
		"""
		room = 'all'
		body = mess.getBody()
		if self.is_room(mess):
			room = str(mess.getFrom()).split('@')[0]
			tokens = body.split(" ")
			tokens.pop(0) # .locks
			if len(tokens) > 0:
				room = tokens.pop(0)
		else:
			tokens = body.split(" ")
			tokens.pop(0) # .locks
			if len(tokens) > 0:
				room = tokens.pop(0)
		try:
			return self.send_to_subscriber(alias, mess, self.get_locks(room))
		except Exception, e:
			return self.send_to_subscriber(alias, mess, str(e))

	def get_locks(self, room):
		locks = self.db.get('locks', {})
		message = ["Existing Locks:"]
		if room == 'all':
			for key in locks:
				room_locks = locks[key]
				for lock, owner, note in room_locks.values():
					message.append("    %s/%s: %s %s" %(
						key, lock, owner, note))
		else:
			room_locks = locks.setdefault(room, {})
			for lock, owner, note in room_locks.values():
				message.append("    %s/%s: %s %s" %(room, lock, owner, note))
		if len(message) == 1:
			message.append("    NONE")
		return '\n'.join(message)

	@botcmd
	def unlock(self, mess, args, alias, **kwargs):
		"""
		Release a lock you have over a resource.
		Only the person who established it can unlock it, but anyone can break it.
		Calling this will broadcast in the room the lock was established in.
		Format: .unlock <lockname>
		"""
		room, owner, lock, _ = self.get_lock_fundamentals(mess, alias)
		try:
			roomjid = self.get_room_jid(room)
			response = self.release_lock(lock, owner, room)
			if self.is_room(mess):
				return response
			else:
				self.send(roomjid, response)
				return response
		except Exception, e:
			return str(e)

	def release_lock(self, lock, owner, room, break_lock=False):
		with self.rlock:
			locks = self.db.get('locks', {})
			room_locks = locks.setdefault(room, {})
			if room_locks.get(lock):
				elock, eowner, enote = room_locks.get(lock)
				if eowner != owner:
					if break_lock:
						try:
							response = "LOCK BROKEN: \n    %s/%s: %s" % (
								room, lock, owner)
							sub = self.get_subscriber(eowner)
							self.send(sub, response)
						except Exception, e:
							print e
					else:
						raise Exception("You don't own that lock!: \n"
							"    %s/%s: %s %s" % (room, lock, eowner, enote))
			else:
				raise Exception("Lock does not exist: \n"
					"    %s/%s" % (room, lock))
			del room_locks[lock]
			self.db['locks'] = locks
			if break_lock:
				return "LOCK BROKEN: \n    %s/%s: %s" % (room, lock, owner)
			else:
				return "Lock released: \n    %s/%s: %s" % (room, lock, owner)

	@botcmd(name='break')
	def break_lock(self, mess, args, alias, **kwargs):
		"""
		Break a lock someone else has over a resource.
		This is bad, but sadly necessary.
		Calling this will broadcast to both the room the lock came from, in the tech room, and if possible a message will be sent to the owner.
		Format: .break <lockname>
		"""
		room, owner, lock, _ = self.get_lock_fundamentals(mess, alias)
		try:
			roomjid = self.get_room_jid(room)
			response = self.release_lock(lock, owner, room, break_lock=True)
			print response
			if self.is_room(mess):
				self.send(self.get_room_jid('knewton-tech'), response)
				return response
			else:
				self.send(roomjid, response)
				self.send(self.get_room_jid('knewton-tech'), response)
				return response
		except Exception, e:
			return str(e)

	def subscribed(self, jid):
		if jid.getDomain() == 'im.partych.at':
			body = "/me is watching %s" %( jid.getNode() )
			self.send(jid, body)

	def get_rooms(self):
		roster = self.conn.Roster.getRoster()
		items = []
		for item in roster.getItems():
			item = xmpp.JID(item)
			if item.getDomain() == 'im.partych.at':
				items.append(item)
		return items

	def get_subscriber(self, subscriber):
		roster = self.conn.Roster.getRoster()
		for item in roster.getItems():
			if subscriber == item:
				return xmpp.JID(item)

	def get_room_jid(self, room):
		roomjids = self.get_rooms()
		for jid in roomjids:
			if jid.getNode() == room:
				return jid
		raise Exception(' '.join([
			"%s is not a room that I'm aware of." % room,
			"Call .rooms for a list"]))

	def alias_to_email(self, alias, room):
		aliases = self.db['aliases']
		room_aliases = aliases.get(room, {})
		if alias in room_aliases:
			sub = room_aliases.get(alias)
			if sub:
				return sub

	def alias_to_subscriber(self, alias, room):
		aliases = self.db['aliases']
		room_aliases = aliases.get(room, {})
		if alias in room_aliases:
			sub = room_aliases.get(alias)
			if sub:
				return self.get_subscriber(sub)

	def send_to_subscriber(self, alias, inmess, outbody):
		subscriber = self.alias_to_subscriber(alias, str(inmess.getFrom()))
		if subscriber:
			self.send(subscriber, outbody)
		else:
			return outbody

	def callback_message(self, conn, mess):
		"""
		Changes the behaviour of the JabberBot in order to allow
		it to answer direct messages. This is used often when it is
		connected in MUCs (multiple users chatroom).
		"""
		message = mess.getBody()
		noreply_unknown = False
		alias = None
		if self.is_room(mess):
			noreply_unknown = True
			m = re.search('\[(.*?)\]', message)
			if m:
				alias = m.group(1)
			message = message[message.find(']')+2:]
			self.handle_repetition(mess, alias, message)
			mess.setBody(message)
		text = super(TechBot, self).callback_message(
			conn, mess, noreply_unknown=noreply_unknown, alias=alias)
		if text:
			return text
		for name in self.content_commands:
			cmd = self.content_commands[name]
			text = cmd(mess)
			if text:
				return text

	def handle_repetition(self, mess, alias, body):
		if self.is_room(mess) and alias:
			with self.rlock:
				last, count = self.last_message.get(alias, (None, 0))
				if last == body:
					count = count + 1
				else:
					count = 1
				if count == 3:
					self.send(
						mess.getFrom(),
						"/me stabs %s in the face for excessive"
						"repetition" % alias)
				self.last_message[alias] = (body, count)

	@contentcmd
	def list_results(self, mess):
		if self.is_room(mess):
			message = mess.getBody().split('\n')
			if message[0].startswith('isting members of'):
				message.pop(0)
				for line in message:
					if line.startswith("Room is invite-only") \
							or line.startswith("Invited:"):
						break
					line = line.replace("(online)", "")
					m = re.search('\* (.*?) \((.*)\)', line)
					if m:
						try:
							user = m.group(1)
							jid = m.group(2)
							room = str(mess.getFrom())
							self.record_alias(user, jid, room)
						except Exception, e:
							print e
				return True

	@contentcmd
	def intentional_deploy_hype(self, mess):
		if self.is_room(mess):
			message = mess.getBody().lower()
			if message.find('deploy!') > -1:
				self.send(mess.getFrom(), select_deployment_hype())
				return True

	@contentcmd
	def deploy_hype(self, mess):
		if self.is_room(mess):
			if random.randint(1, 100) >= 80:
				message = mess.getBody().lower()
				if message.find('deploy') > -1:
					self.send(mess.getFrom(), select_deployment_hype())
					return True

	@contentcmd
	def nods(self, mess):
		if self.is_room(mess):
			message = mess.getBody().lower()
			if message.find('?') > -1:
				if random.randint(1, 100) >= 99:
					self.send(mess.getFrom(), "/me nods")
					return True

	@contentcmd
	def smiles(self, mess):
		if self.is_room(mess):
			message = mess.getBody().lower()
			if message.find('techbot++') > -1:
				self.send(mess.getFrom(), "/me smiles")
				return True

	@contentcmd
	def frowns(self, mess):
		if self.is_room(mess):
			message = mess.getBody().lower()
			if message.find('techbot--') > -1:
				self.send(mess.getFrom(), "/me frowns")
				return True

	@contentcmd
	def damnit(self, mess):
		if self.is_room(mess):
			damnit_list = ['jon!', 'sid!']
			message = mess.getBody().lower()
			if message in damnit_list:
				self.send(mess.getFrom(), "Damnit %s" % message)
				return True

	def is_room(self, mess):
		if mess.getFrom().getDomain() == 'im.partych.at':
			self.populate_room_users(mess)
			return True
		return False

	def populate_room_users(self, mess):
		body = mess.getBody()
		m = re.search('\[(.*?)\]', body)
		if m:
			user = m.group(1)
			if not self.check_user(user, str(mess.getFrom())):
				self.send(mess.getFrom(), "/list")

	def check_user(self, user, room):
		if not self.db.has_key('aliases'):
			with self.rlock:
				self.db['aliases'] = {}
		if not self.db['aliases'].has_key(room):
			with self.rlock:
				rooms = self.db['aliases']
				rooms[room] = {}
				self.db['aliases'] = rooms
		if not self.db['aliases'][room].has_key(user):
			return False
		return True

	def record_alias(self, user, jid, room):
		with self.rlock:
			aliases = self.db['aliases']
			room_aliases = aliases.get(room, {})
			room_aliases[user] = jid
			self.db['aliases'] = aliases

def select_hype():
	hype = [
		"/me pumps its fist in the air (Yeah!!)",
		"Sick!",
		"You guys totally destroyed that!"
		"Aaaaay! You know what it is!",
		"Ohhhh! GET IT!",
		"Ha haaa! Yaaay-uhhh!",
		"Yoooooouuuuu!",
		"Get 'em up! GET YOUR HANDS UP!",
		"Get money!",
		"Ballllllin!",
		"Jeah!",
		"Get it!",
		"That's my dog! That's my boy right there!",
		"Put your hands together for this one right here!",
		"/me just popped a bottle",
		"/me is making it rain",
		"/me is getting so low right now"]
	return random.choice(hype)

def select_deployment_hype():
	hype = [
		"/me is looking forward to this patch",
		"/me crosses its fingers for this release",
		"/me waits to see if this deploy works",
		"/me gives you a high five for getting this code out",
		"Woop Woop! get that code out!",
		select_hype()
		]
	return random.choice(hype)
