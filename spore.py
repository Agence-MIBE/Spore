from twisted.internet import protocol, reactor

# Protocol instance is started for each connection
class FungusProtocol(protocol.Protocol):
	def __init__(self, factory):
		self.factory = factory
		self.num = 0							# Unique connection ID number
		# If data is received befor the connection is made (why would that ever happen?)
		# then this ID will be invalid

	def connectionMade(self):
		# Add to list of connections
		self.factory.numConnections += 1				# Count the number of open connections
		self.num = len(self.factory.connections)			# Unique connection ID number
		self.factory.connections[ self.num ] = self			# Add this connection to the list
		
		# Send welcome message
		self.transport.write( b'Welcome to the fungal server\r\n' )	# Byte string instead of unicode string
		message = 'There are currently %i connections\r\n' % (self.factory.numConnections)
		self.transport.write( message.encode("utf-8") )
		message = 'This is connection number %i\r\n' % (self.num)
		self.transport.write( message.encode("utf-8") )
	
	def connectionLost(self, reason):
		self.factory.numConnections -= 1				# Remove connection from count
		del self.factory.connections[ self.num ]			# Remove self from list

	def dataReceived(self, data):
		print(data)
		if b'exit' in data:
			self.transport.write( b'Bye\r\n' )
			self.transport.loseConnection()
		for num, connection in self.factory.connections.items():
			if connection != self:
				connection.transport.write(data)

class FungusFactory(protocol.Factory):
	numConnections = 0							# Count of open connections
	connections = {}							# List (dictionary) of connections (protocol objects)

	def buildProtocol(self, addr):
		return FungusProtocol(self)

reactor.listenTCP(1701, FungusFactory())
reactor.run()
