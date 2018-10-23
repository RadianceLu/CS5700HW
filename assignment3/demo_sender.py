# Usage: python demo_sender.py [dummy|ss|gbn]
import sys
import util


if __name__ == '__main__':
  if len(sys.argv) != 2:
    print('Usage: python demo_sender.py [dummy|ss|gbn]')
    sys.exit(1)

  transport_layer = None
  transport_layer_name = sys.argv[1]
  try:
    transport_layer = util.get_transport_layer('sender',
                                               transport_layer_name,
                                               None)
    for i in range(20):
      msg = 'MSG:' + str(i)
      print(msg)
      while not transport_layer.send(str.encode(msg)):
        pass
  finally:
    if transport_layer:
      transport_layer.shutdown()
