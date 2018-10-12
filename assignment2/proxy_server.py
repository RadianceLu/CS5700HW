import socket
import struct
import _thread
import time
import sys
import logging

host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
host_port = 8181
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host_ip, host_port))
s.listen()
print('Proxy server started. Waiting for connection...')

def now():
	return time.ctime(time.time())

bufsize = 1024

def handler(conn, addr):
	# Read the request line and header fields until two consecutive new lines 
	byte_array = bytearray(conn.recv(bufsize))
	while get_subarray(byte_array, "\r\n\r\n".encode('utf-8')) == -1:
		byte_array.extend(conn.recv(bufsize))
	request_line = byte_array[0:get_subarray(byte_array, "\r\n".encode('utf-8'))].decode('utf-8')
	request = request_line.split(' ')

	response = bytearray()
	# If the request method is not "GET" 
    # Return an error HTTP response with the status code "HTTP_BAD_METHOD"
	if request[0] != "GET":
		error_message = "HTTP/1.1 405 HTTP_BAD_METHOD\r\nConnection: close\r\n\r\n"
		response = error_message.encode('utf-8')
	else:
		# Make TCP connection to the "real" Web server
		real_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		url = request[1].split('/')
		server_name = url[2]
		real_server_socket.connect((server_name, 80))

		# Send over an HTTP request
		http_version = request[2]
		path = ""
		for str in url[3:]:
			path += "/" + str
		get_request = 'Get ' + path + ' ' + http_version + '\r\n' + 'Host: ' + server_name + '\r\n' + 'Connection: close\r\nAccept-Charset: ISO-8859-1, utf-8\r\n\r\n'
		real_server_socket.sendall(get_request.encode('utf-8'))

		# Receive the server's response
		while True:
			data = real_server_socket.recv(bufsize)
			if not data:
				break
			response.extend(data)

		logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
		logging.warning('GET object %s from host %s', url[len(url) - 1], server_name)

		# Close the TCP connection to the server
		real_server_socket.close()

	# Send the server's response back to the client
	conn.sendall(response)
	# Close the connection socket to the client
	conn.close()

def get_subarray(array, target):
	# return true if target exists in array
	for i in range(len(array) - len(target) + 1):
		if array[i : i + len(target)] == target:
			return i
	return -1

while True:
	conn, addr = s.accept()
	_thread.start_new_thread(handler, (conn, addr))