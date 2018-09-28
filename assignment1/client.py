import socket
import sys
import struct

#connect
server_ip = '10.138.0.3'
server_port = 8181

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((server_ip, server_port))
print('Connected to server ', server_ip, ':', server_port)

#get input
expressions = sys.argv[1].split(',')
print('expressions: ', expressions)

request = bytearray()
#number of expressions
request.extend(struct.pack('!h', len(expressions))) 
for ex in expressions:
	ex_byte = ex.encode('utf-8')
	#length of every expression
	request.extend(struct.pack('!h', len(ex_byte)))
	#expression representation
	request.extend(ex_byte)

#send requests to server
s.sendall(request)

#receive response
bufsize = 16
used_bytes = 0
num_of_expression_to_receive = 0
num_of_received_expression = 0
len_of_next_expression = 0
bytes_of_expression_length = 2
bytes_of_expression_number = 2
response = bytearray()
result = []

while True:
	# check if it can receive expression number
	if len(response) >= 2 and num_of_expression_to_receive == 0:
		num_of_expression_to_receive = struct.unpack('!h', response[0:bytes_of_expression_number])[0]
		used_bytes += bytes_of_expression_number
	#check if it can receive expression length
	elif len(response) - used_bytes >= 2 and len_of_next_expression == 0:
		len_of_next_expression = struct.unpack('!h', response[used_bytes:(used_bytes + bytes_of_expression_length)])[0]
		used_bytes += bytes_of_expression_length
	#check if it can receive expression result
	elif len_of_next_expression > 0 and len(response) - used_bytes >= len_of_next_expression:
		result.append(response[used_bytes:(used_bytes + len_of_next_expression)].decode('utf-8'))
		num_of_received_expression += 1
		used_bytes += len_of_next_expression
		len_of_next_expression = 0

		if num_of_expression_to_receive != 0 and num_of_expression_to_receive == num_of_received_expression:
			break
	else:
		response.extend(s.recv(bufsize))

#close
s.close()
print('result: ', result)

