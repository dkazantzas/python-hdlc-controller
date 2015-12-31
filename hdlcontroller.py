#!/usr/bin/env python3

from yahdlc import *
from threading import Thread, Event, Lock
from time import sleep

class HDLController:
	"""
	An HDLC controller based on python4yahdlc.
	"""

	MAX_SEQ_NO = 8

	def __init__(self, read_func, write_func, window=3):
		if not hasattr(read_func, '__call__'):
			raise TypeError('The read function parameter is not a callable object')
		if not hasattr(write_func, '__call__'):
			raise TypeError('The write function parameter is not a callable object')

		self.read = read_func
		self.write = write_func

		self.window = window
		self.senders = dict()
		self.send_lock = Lock()
		self.new_seq_no = 0

		self.send_callback = None
		self.receive_callback = None

		self.receiver = None

	def start(self):
		"""
		Start HDLC controller's threads.
		"""

		self.receiver = self.Receiver(
			self.read,
			self.write,
			self.send_lock,
			self.senders,
			callback=self.receive_callback,
		)

		self.receiver.start()

	def stop(self):
		"""
		Stop HDLC controller's threads.
		"""

		self.receiver.join()

		for s in self.senders.values():
			s.join()

	def set_send_callback(self, callback):
		"""
		Set the send callback function.

		If the HDLC controller has already
		been started, the new callback
		function will be take into account
		for the next data frames to send.
		"""

		if not hasattr(callback, '__call__'):
			raise TypeError('The callback function parameter is not a callable object')

		self.send_callback = callback

	def set_receive_callback(self, callback):
		"""
		Set the receive callback function.

		This method has to be called before
		starting the HDLC controller.
		"""

		if not hasattr(callback, '__call__'):
			raise TypeError('The callback function parameter is not a callable object')

		self.receive_callback = callback

	def send(self, data):
		"""
		Send a new data frame.

		This method will block until a new room is
		available for a new sender. This limit is
		determined by the size of the window.
		"""

		while len(self.senders) >= self.window:
			pass

		self.senders[self.new_seq_no] = self.Sender(
			self.write,
			self.send_lock,
			data,
			self.new_seq_no,
			callback=self.send_callback,
		)

		self.senders[self.new_seq_no].start()
		self.new_seq_no = (self.new_seq_no + 1) % HDLController.MAX_SEQ_NO

	class Sender(Thread):
		"""
		Thread used to send HDLC frames.
		"""

		def __init__(self, write_func, send_lock, data, seq_no, callback=None):
			super().__init__()
			self.write = write_func
			self.send_lock = send_lock
			self.data = data
			self.seq_no = seq_no
			self.callback = callback
			self.ack = Event()

		def run(self):
			with self.send_lock:
				self.__send_data()

			while not self.ack.isSet():
				pass

		def join(self, timeout=None):
			"""
			Stop the current thread.
			"""

			self.ack.set()
			super().join(timeout)

		def ack_received(self):
			"""
			Inform the sender that the ack frame
			has been received which has the
			consequence of stopping the current
			thread.
			"""

			self.join()

		def nack_received(self):
			"""
			Inform the sender that a nack frame
			has been received which has the
			consequence of resending the data
			frame.
			"""

			with self.send_lock:
				self.__send_data()

		def __send_data(self):
			"""
			Send a new data frame.
			"""

			if self.callback != None:
				self.callback(self.data)

			self.write(frame_data(self.data, FRAME_DATA, self.seq_no))

	class Receiver(Thread):
		"""
		Thread used to receive HDLC frames.
		"""

		def __init__(self, read_func, write_func, send_lock, senders_list, callback=None):
			super().__init__()
			self.read = read_func
			self.write = write_func
			self.send_lock = send_lock
			self.senders = senders_list
			self.callback = callback
			self.stop_receiver = Event()

		def run(self):
			while not self.stop_receiver.isSet():
				try:
					data, type, seq_no = get_data(self.read())

					if type == FRAME_DATA:
						if self.callback != None:
							self.callback(data)

						with self.send_lock:
							self.__send_ack((seq_no + 1) % HDLController.MAX_SEQ_NO)
					elif type == FRAME_ACK:
						seq_no_sent = (seq_no - 1) % HDLController.MAX_SEQ_NO
						self.senders[seq_no_sent].ack_received()
						del self.senders[seq_no_sent]
					elif type == FRAME_NACK:
						self.senders[seq_no].nack_received()
					else:
						raise TypeError('Bad frame type received')
				except MessageError:
					# No HDLC frame detected
					pass
				except KeyError:
					# Drop bad (n)ack
					pass
				except FCSError:
					with self.send_lock:
						self.__send_nack(seq_no)
				finally:
					# 200 µs
					sleep(200 / 1000000.0)

		def join(self, timeout=None):
			"""
			Stop the current thread.
			"""

			self.stop_receiver.set()
			super().join(timeout)

		def __send_ack(self, seq_no):
			"""
			Send a new ack frame.
			"""

			self.write(frame_data('', FRAME_ACK, seq_no))

		def __send_nack(self, seq_no):
			"""
			Send a new nack frame.
			"""

			self.write(frame_data('', FRAME_NACK, seq_no))

if __name__ == '__main__':
	import serial
	from sys import stdout, stderr
	from argparse import ArgumentParser

	ap = ArgumentParser(
		description='HDLC controller example',
		epilog="Example: ./hdlcontroller.py -d /dev/ttyUSB0 -b 115200 -m 'Hello world!'",
	)
	ap.add_argument('-d', '--device', default='/dev/ttyACM0', help='serial device to use (default: /dev/ttyACM0)')
	ap.add_argument('-b', '--baudrate', type=int, default='9600', help='serial baudrate value (default: 9600)')
	ap.add_argument('-t', '--timeout', type=int, default='0', help='serial read timeout value (default: 0)')
	ap.add_argument('-m', '--message', default='test', help='test message to send (default: test)')
	ap.add_argument('-i', '--interval', type=float, default='1.0', help='sending interval between two data frames (default: 1.0)')
	args = vars(ap.parse_args())

	# Serial port configuration
	ser = serial.Serial()
	ser.port = args['device']
	ser.baudrate = args['baudrate']
	ser.timeout = args['timeout']

	stdout.write('[*] Connection ...\n')

	try:
		ser.open()
	except serial.serialutil.SerialException as e:
		stderr.write('[x] Serial connection problem : {0}\n'.format(e))
		exit(1)

	def read_uart():
		return ser.read(ser.inWaiting())

	def send_callback(data):
		print('> {0}'.format(data))

	def receive_callback(data):
		print('< {0}'.format(data))

	try:
		hdlc_c = HDLController(read_uart, ser.write)
		hdlc_c.set_send_callback(send_callback)
		hdlc_c.set_receive_callback(receive_callback)
		hdlc_c.start()
		while True:
			hdlc_c.send(args['message'])
			sleep(args['interval'])
	except KeyboardInterrupt:
		stdout.write('[*] Bye !\n')
		hdlc_c.stop()
		ser.close()
