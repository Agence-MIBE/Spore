#!/usr/bin/python
#
# Spore
#
# Matchmaking and relay server for Fungus.

from random import randint

from twisted.internet import protocol, reactor
from twisted.protocols.basic import LineReceiver

maxPlayers = 2

# Protocol instance is started for each connection
class FungusProtocol(LineReceiver):
	def __init__(self, factory):
		self.factory = factory
		self.num = 0							# Unique connection ID number
		# If data is received before the connection is made (why would that ever happen?)
		# then this ID will be invalid
		self.name = None						# Username
		self.req_players = 2						# Requested number of players for game
		self.state = "UNCONNECTED"					# Possible states: UNCONNECTED, LOGIN, WAITING, GAME
		self.login_request = None					# Current piece of information being requested for login
		self.game = None						# Game this player is playing
	
	def transmit(self, message):
		# Python 3 workaround
		# Converts unicode strings to byte strings before sending
		# Twisted was written for Python 2, where strings are bytestrings
		# but in Python 3 they are unicode.
		self.sendLine(message.encode("utf-8"))
	
	def txOtherPlayers(self, message):
		# Send a message to all other players in the game
		for player in self.game:
			if player != self:
				player.transmit(message)

	def connectionMade(self):
		# Log incoming IP address
		self.ip = self.transport.getPeer().host
		self.port = self.transport.getPeer().port
		print( ':: Connection from %s:%i' % (self.ip,self.port) )

		# Add to list of connections
		self.factory.numConnections += 1				# Count the number of open connections
		for x in range(len(self.factory.connections)+1):		# Generate unique connection ID number
			if x not in self.factory.connections:
				self.num = x
				break
		self.factory.connections[ self.num ] = self			# Add this connection to the list
		
		# Change state
		self.state = 'LOGIN'						# Start login process
		self.login_request = 'USERNAME'					# Begin waiting for username

		# Send welcome message
		self.transmit( '\r\nWelcome to the fungal server' )
		#self.transport.write( message.encode("utf-8") )
		self.transmit( 'There are currently %i connections' % (self.factory.numConnections) )
		self.transmit( 'This is connection number %i' % (self.num) )
		self.transmit( 'Address: %s Port: %i' % (self.ip, self.port) )
		self.transmit( 'USERNAME:' )					# Text in CAPS is client commands
	
	def connectionLost(self, reason):
		print( ':: Disconnect %s at %s:%i' % (self.name,self.ip,self.port) )
		self.factory.numConnections -= 1				# Remove connection from count
		del self.factory.connections[ self.num ]			# Remove self from list

		if self.game:
			# Inform all other players of disconnect
			self.txOtherPlayers( 'Player %i disconnected.' % (self.game.index(self)) )
			# Remove self from game
			self.game.remove(self)
			self.factory.checkEndgame( self.game )

	#def dataReceived(self, data):
	def lineReceived(self, data):
		data = data.decode('utf-8')					# Convert bytestring back to normal (unicode) string

		if self.state == 'LOGIN':
			self.login(data)
		elif self.state == 'GAME':
			self.relay(data)
	
	def login(self, data):
		if self.login_request == 'USERNAME':
			self.name = data					# Set username
			self.login_request = 'NUM_PLAYERS'			# Begin waiting for requested number of players
			self.transmit( 'NUM_PLAYERS:' )
		elif self.login_request == 'NUM_PLAYERS':
			try:
				self.req_players = int(data[0])			# Set number of players in game
			except ValueError:					# Make sure client is sending integers
				self.transmit( 'Error: That was not a number. Try again.' )
				return
			# Make sure value is within range
			#if self.req_players < 2 or self.req_players > 4:
			#	self.transmit( 'Error: Must choose either 2, 3, or 4 players.' )
			#	return
			if self.req_players != 2:
				self.transmit( 'ERROR: Only supporting 2 player games right now' )
				return
			# End login process and start game
			self.login_request = None
			self.state = 'WAITING'
			self.transmit( 'Access granted, %s.' % (self.name) )
			print( ':: Login from %s for %i player game' % (self.name,self.req_players) )
			self.factory.newGame.append( self )			# Add player to staging game
			if len(self.factory.newGame) >= maxPlayers:		# Start game if it has enough players
				self.factory.startGame()

	def relay(self, data):
		# Interpret commands
		if 'exit' in data:
			self.transmit( 'Bye' )
			self.transport.loseConnection()
		# Relay data to peers
		self.txOtherPlayers(data)

# What is a factory? Twisted confuses me.
class FungusFactory(protocol.Factory):
	numConnections = 0							# Count of open connections
	connections = {}							# List (dictionary) of connections (protocol objects)
	newGame = []								# Game waiting for enough players
	games = []								# List of games in progress

	def buildProtocol(self, addr):
		return FungusProtocol(self)
	
	def startGame(self):
		game = self.newGame
		self.games.append(game)						# Move game to in progress
		self.newGame = []						# Reset staging game
		start_player = randint(0,maxPlayers)				# Choose random starting player
		print( ':: Game #%i starting between ' % (self.games.index(game)) , end="" )
		for player in game:
			print(player.name, end=", ")
			player.game = game
			player.state = "GAME"
			player.transmit( 'Enough players have arrived. Game started' )
			player.transmit( 'Your are player number %i' % (game.index(player)) )
			player.transmit( 'YOUR_NUM: %i' % (game.index(player)) )
			player.transmit( 'START: %i' % (start_player) )
		print( 'starting with player %i' % (start_player) )
	
	def checkEndgame(self, game):
		# If all but one player has disconnected
		# ( do not make this <=1 or it will cause a loop )
		if len(game) == 1:
			print( ':: Game #%i ended' % (self.games.index(game)) )
			# Disconnect all remaining players
			for player in game:
				player.transmit( 'Game Over' )
				player.transport.loseConnection()
			# Remove game from list
			self.games.remove(game)


reactor.listenTCP(1701, FungusFactory())
reactor.run()
