import socket
import struct
import _thread
import time

host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
host_port = 8181
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host_ip, host_port))
s.listen()
print('\nServer started. Waiting for connection...\n')

#current time on the server
def now():
	return time.ctime(time.time())

bufsize = 16
def handler(conn, addr):
	num_of_expression_to_receive = 0
	num_of_received_expression = 0
	len_of_next_expression = 0
	used_bytes = 0
	request = bytearray()
	response = bytearray()

	while True:
		#check number of expressions
		if len(request) >= 2 and num_of_expression_to_receive == 0:
			response[0:2] = request[0:2]
			num_of_expression_to_receive = struct.unpack('!h', request[0:2])[0]
			used_bytes += 2
		#check length of expression
		elif len(request) - used_bytes >= 2 and len_of_next_expression == 0:
			len_of_next_expression = struct.unpack('!h', request[used_bytes:(used_bytes+2)])[0]
			used_bytes += 2
		#check expression representation
		elif len_of_next_expression > 0 and len(request) - used_bytes >= len_of_next_expression:
			current = request[used_bytes:(used_bytes + len_of_next_expression)].decode('utf-8')
			value = calculate(current)
			value_bytes = str(value).encode('utf-8')
			response.extend(struct.pack('!h', len(value_bytes)))
			response.extend(value_bytes)
			num_of_received_expression += 1
			used_bytes += len_of_next_expression
			len_of_next_expression = 0

			if num_of_expression_to_receive != 0 and num_of_expression_to_receive == num_of_received_expression:
				break
		else:
			request.extend(conn.recv(bufsize))

	conn.sendall(response)
	conn.close()

def calculate(expression):
	stack, num, operator = [], 0, "+"
	for i in range(len(expression)):
		if expression[i].isdigit():
			num = num * 10 + ord(expression[i]) - ord("0")
		if not expression[i].isdigit() or i == len(expression) - 1:
			if operator == "-":
				stack.append(-num)
			elif operator == "+":
				stack.append(num)
			elif operator == "*":
				stack.append(stack.pop() * num)
			else:
				stack.append(stack.pop() // num)
			operator = expression[i]
			num = 0

	return sum(stack)

while True:
	conn, addr = s.accept()
	print('server connected by', addr, 'at', now())
	_thread.start_new_thread(handler, (conn, addr))