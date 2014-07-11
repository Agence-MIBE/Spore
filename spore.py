# Spore
#
# Matchmaking and relay server for Fungus.

from twisted.internet import protocol, reactor
from twisted.protocols.basic import LineReceiver

# Protocol instance is started for each connection
class FungusProtocol(LineReceiver):
	def __init__(self, factory):
		self.factory = factory
		self.num = 0							# Unique connection ID number
		# If data is received before the connection is made (why would that ever happen?)
		# then this ID will be invalid
		self.name = None						# Username
		self.state = "UNCONNECTED"					# Possible states: UNCONNECTE, LOGIN, NOGAME, GAME
	
	def transmit(self, message):
		# Python 3 workaround
		# Converts unicode strings to byte strings before sending
		# Twisted was writtern for Python 2, where strings are bytestrings
		# but in Python 3 they are unicode.
		self.sendLine(message.encode("utf-8"))


	def connectionMade(self):
		# Log incoming IP address
		self.ip = self.transport.getPeer().host
		self.port = self.transport.getPeer().port

		# Add to list of connections
		self.factory.numConnections += 1				# Count the number of open connections
		for x in range(len(self.factory.connections)+1):		# Generate unique connection ID number
			if x not in self.factory.connections:
				self.num = x
				break
		self.factory.connections[ self.num ] = self			# Add this connection to the list
		
		# Change state
		self.state = "LOGIN"						# Begin waiting for username

		# Send welcome message
		self.transmit( '\r\nWelcome to the fungal server' )
		#self.transport.write( message.encode("utf-8") )
		self.transmit( 'There are currently %i connections' % (self.factory.numConnections) )
		self.transmit( 'This is connection number %i' % (self.num) )
		self.transmit( 'Address: %s Port: %i' % (self.ip, self.port) )
		message = 'Username: '
		self.transport.write( message.encode("utf-8") )
	
	def connectionLost(self, reason):
		self.factory.numConnections -= 1				# Remove connection from count
		del self.factory.connections[ self.num ]			# Remove self from list

	#def dataReceived(self, data):
	def lineReceived(self, data):
		data = data.decode("utf-8")					# Convert bytestring back to normal (unicode) string

		if self.state == "LOGIN":
			self.name = data
			self.state = "NOGAME"
			self.transmit( 'Access granted, %s.' % (self.name) )
		else:
			# Interpret commands
			if 'exit' in data:
				self.transmit( 'Bye' )
				self.transport.loseConnection()
			# Relay data to peers
			for num, connection in self.factory.connections.items():
				if connection != self:
					connection.transmit(data)

# What is a factory? Twisted confuses me.
class FungusFactory(protocol.Factory):
	numConnections = 0							# Count of open connections
	connections = {}							# List (dictionary) of connections (protocol objects)

	def buildProtocol(self, addr):
		return FungusProtocol(self)

reactor.listenTCP(1701, FungusFactory())
reactor.run()
