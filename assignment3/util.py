import config
import dummy
import gbn
import ss
import threading
import time


# Factory method to construct transport layer.
def get_transport_layer(sender_or_receiver,
                        transport_layer_name,
                        msg_handler):
  assert sender_or_receiver == 'sender' or sender_or_receiver == 'receiver'
  if sender_or_receiver == 'sender':
    return _get_transport_layer_by_name(transport_layer_name,
                                        config.SENDER_IP_ADDRESS,
                                        config.SENDER_LISTEN_PORT,
                                        config.RECEIVER_IP_ADDRESS,
                                        config.RECEIVER_LISTEN_PORT,
                                        msg_handler)
  if sender_or_receiver == 'receiver':
    return _get_transport_layer_by_name(transport_layer_name,
                                        config.RECEIVER_IP_ADDRESS,
                                        config.RECEIVER_LISTEN_PORT,
                                        config.SENDER_IP_ADDRESS,
                                        config.SENDER_LISTEN_PORT,
                                        msg_handler)


def _get_transport_layer_by_name(name, local_ip, local_port, 
                                 remote_ip, remote_port, msg_handler):
  assert name == 'dummy' or name == 'ss' or name == 'gbn'
  if name == 'dummy':
    return dummy.DummyTransportLayer(local_ip, local_port,
                                     remote_ip, remote_port, msg_handler)
  if name == 'ss':
    return ss.StopAndWait(local_ip, local_port,
                          remote_ip, remote_port, msg_handler)
  if name == 'gbn':
    return gbn.GoBackN(local_ip, local_port,
                       remote_ip, remote_port, msg_handler)

def make_data_packet(type, sequence, msg):
  result = bytearray()
  type_bytes = type.to_bytes(2, BIG_ENDIAN)
  result.extend(type_bytes)
  sequence_bytes = sequence.to_bytes(2, BIG_ENDIAN)
  result.extend(sequence_bytes)
  checksum = make_checksum(type, sequence, msg)
  checksum_bytes = checksum.to_bytes(2, BIG_ENDIAN)
  result.extend(checksum_bytes)
  result.extend(msg)
  return result

def make_ack_packet(type, sequence):
  result = bytearray()
  type_bytes = type.to_bytes(2, BIG_ENDIAN)
  result.extend(type_bytes)
  sequence_bytes = sequence.to_bytes(2, BIG_ENDIAN)
  result.extend(sequence_bytes)
  checksum = type + sequence
  checksum_bytes = checksum.to_bytes(2, BIG_ENDIAN)
  result.extend(checksum_bytes)
  return result

def make_checksum(type, sequence, msg):
  return (type + sequence + calc_payload_sum(msg)) % HASH_SIZE

def calc_payload_sum(msg):
  total = 0
  data = bytearray()
  data.extend(msg)
  if len(msg) % 2 == 1:
    data.extend((1).to_bytes(1, BIG_ENDIAN))
  for i in range(0, len(data), 2):
    total = total + int.from_bytes(data[i:i + 2], BIG_ENDIAN)
  return total

def now():
  return int(round(time.time() * 1000))

def valid_data(msg):
  type = int.from_bytes(msg[0:2], BIG_ENDIAN)
  sequence = int.from_bytes(msg[2:4], BIG_ENDIAN)
  checksum = int.from_bytes(msg[4:6], BIG_ENDIAN)
  payload = msg[6::]
  payload_sum = calc_payload_sum(payload)
  if type == config.MSG_TYPE_DATA and checksum == (type + sequence + payload_sum) % HASH_SIZE:
    return True
  return False

def valid_ack(msg):
  type = int.from_bytes(msg[0:2], BIG_ENDIAN)
  sequence = int.from_bytes(msg[2:4], BIG_ENDIAN)
  checksum = int.from_bytes(msg[4:6], BIG_ENDIAN)
  if type == config.MSG_TYPE_ACK and checksum == type + sequence:
    return True
  return False

def get_sequence(msg):
  return int.from_bytes(msg[2:4], BIG_ENDIAN)

def get_payload(msg):
  return msg[6::]

BIG_ENDIAN = "big"
HASH_SIZE = 65536

# Convenient class to run a function periodically in a separate
# thread.
class PeriodicClosure:
  def __init__(self, handler, interval_sec):
    self._handler = handler
    self._interval_sec = interval_sec
    self._lock = threading.Lock()
    self._timer = None

  def _timeout_handler(self):
    with self._lock:
      self._handler()
      self.start()

  def start(self):
    self._timer = threading.Timer(self._interval_sec, self._timeout_handler)
    self._timer.start()

  def stop(self):
    with self._lock:
      if self._timer:
        self._timer.cancel()
