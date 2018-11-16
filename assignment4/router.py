import os.path
import socket
import table
import threading
import util
import collections

_CONFIG_UPDATE_INTERVAL_SEC = 5

_MAX_UPDATE_MSG_SIZE = 1024
_BASE_ID = 8000
BIG_ENDIAN = "big"

def _ToPort(router_id):
  return _BASE_ID + router_id

def _ToRouterId(port):
  return port - _BASE_ID

def _ValidPacket(packet):
  if len(packet) % 2 != 0:
    return False
  if len(packet) < 2:
    return False

  entry_count = int.from_bytes(packet[0:2], BIG_ENDIAN)
  if len(packet) - 2 != entry_count * 4:
    return False

  return True


def _GetDistance(packet):
	entry_count = int.from_bytes(packet[0:2], BIG_ENDIAN)
	result = {}

	for i in range(entry_count): 
		id = int.from_bytes(packet[2 + 4 * i : 4 + 4 * i], BIG_ENDIAN)
		cost = int.from_bytes(packet[4 + 4 * i : 6 + 4 * i], BIG_ENDIAN)
		result[id] = cost

	return result

class Router:
  def __init__(self, config_filename):
    # ForwardingTable has 3 columns (DestinationId,NextHop,Cost). It's
    # threadsafe.
    self._forwarding_table = table.ForwardingTable()
    # Config file has router_id, neighbors, and link cost to reach
    # them.
    self._config_filename = config_filename
    self._config_snapshot = []
    self._config_table = {}
    self._router_id = None
    # Socket used to send/recv update messages (using UDP).
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


  def start(self):
    # Start a periodic closure to update config.
    self._config_updater = util.PeriodicClosure(
        self.load_config, _CONFIG_UPDATE_INTERVAL_SEC)
    self._config_updater.start()
    # TODO: init and start other threads.
    self.buffer_lock = threading.Lock()
    self.msg_buffer = collections.deque(maxlen = 8)
    self.stop_accept_packet = False
    thread1 = threading.Thread(target = self._PacketReader())
    thread1.start()


  def stop(self):
    if self._config_updater:
      self._config_updater.stop()
    # TODO: clean up other threads.
    self.stop_accept_packet = True


  def _PacketReader(self): 
    while not self.stop_accept_packet:
      has_msg = False
      with self.buffer_lock:
        if len(self.msg_buffer) > 0:
          has_msg = True
      if has_msg:
        self.Handle_Arrival_Msg()
        continue
      try:
        msg, addr = self._socket.recvfrom(_MAX_UPDATE_MSG_SIZE)
        with self.buffer_lock:
          if len(self.msg_buffer) < self.msg_buffer.maxlen:
            self.msg_buffer.append((msg, addr[1]))
      except socket.timeout:
        pass


  def Handle_Arrival_Msg(self):
    packet = ''
    port = 0
    with self.buffer_lock:
      if len(self.msg_buffer) > 0:
        packet, port = self.msg_buffer.popleft()
    if _ValidPacket(packet):
      distance = _GetDistance(packet)
      self.update_forwarding_table(distance, port)


  def update_forwarding_table(self, distance, port):
    neighbor_id = _ToRouterId(port)
    old_snapshot = self._forwarding_table.snapshot()
    old_table = {}

    for (dest, next_hop, cost) in old_snapshot:
      if next_hop == neighbor_id:
        cost = self._config_table[neighbor_id] + distance[dest]
      old_table[dest] = (next_hop, cost)

    for dest_id in distance:
      if dest_id in old_table:
        next_hop, cost = old_table[dest_id]
        if distance[dest_id] + self._config_table[neighbor_id] < cost:
          old_table[dest_id] = (neighbor_id, distance[dest_id] + self._config_table[neighbor_id])
      else:
        old_table[dest_id] = (neighbor_id, distance[dest_id] + self._config_table[neighbor_id])

    new_snapshot = []
    for router_id in old_table:
      h, c = old_table[router_id]
      new_snapshot.append((router_id, h, c))
    self._forwarding_table.reset(new_snapshot)


  def broadcast(self, neighbors):
    packet = self.wrap_table()
    for neighbor_id in neighbors:
      self._socket.sendto(packet, ('localhost', _ToPort(neighbor_id)))


  def wrap_table(self):
    packet = bytearray()
    entry_count = self._forwarding_table.size()
    packet.extend(entry_count.to_bytes(2, BIG_ENDIAN))
    snapshot = self._forwarding_table.snapshot()

    for (dest, next_hop, cost) in snapshot:
      packet.extend(dest.to_bytes(2, BIG_ENDIAN))
      packet.extend(cost.to_bytes(2, BIG_ENDIAN))
    return packet

  def load_config(self):
    assert os.path.isfile(self._config_filename)
    with open(self._config_filename, 'r') as f:
      router_id = int(f.readline().strip())
      # Only set router_id when first initialize.
      if not self._router_id:
        self._socket.bind(('localhost', _ToPort(router_id)))
        self._router_id = router_id
      # TODO: read and update neighbor link cost info.
      new_snapshot = []
      new_snapshot.append((router_id, router_id, 0))
      new_table = {}
      new_table[router_id] = 0
      neighbors = []

      line = f.readline()
      while line:
      	id = int(line.split(',')[0])
      	cost = int(line.split(',')[1])
      	new_snapshot.append((id, id, cost))
      	new_table[id] = cost
      	neighbors.append(id)
      	line = f.readline()

      if set(new_snapshot) != set(self._config_snapshot):
      	self._config_snapshot = new_snapshot
      	self._config_table = new_table
      	self._forwarding_table.reset(new_snapshot)
      	print(new_snapshot)
      print(self._forwarding_table)
      self.broadcast(neighbors)

  
