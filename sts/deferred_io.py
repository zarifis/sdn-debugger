'''
Created on Feb 25, 2012

@author: rcs
'''
import exceptions
import sys
import errno
import logging
import Queue
import socket

from pox.lib.util import assert_type, makePinger
from pox.lib.recoco import Select, Task
from pox.lib.ioworker.io_worker import IOWorker

log = logging.getLogger()

class DeferredIOWorker(object):
  '''
  Wrapper class for RecocoIOWorkers.
  
  Rather than actually sending/receiving right away, queue the messages.
  Then there are separate methods for actually sending the messages via
  the wrapped io_worker
  
  io_worker: io_worker to wrap
  call_later: recoco.Scheduler's call_later factory method for scheduling/thread-safety
  '''
  def __init__(self, io_worker, call_later):
    self._io_worker = io_worker
    self._io_worker.set_receive_handler(self.io_worker_receive_handler)
    self._call_later = call_later
    # Thread-safe read and write queues of indefinite length
    self._receive_queue = Queue.Queue()
    self._send_queue = Queue.Queue()
    # Read buffer that we present to clients
    self._receive_buf = ""

  def permit_send(self):
    '''
    deque()s the first element of the write queue, and actually sends it
    across the wire.
    
    raises an exception if the write queue is empty
    '''
    message = self._send_queue.get()
    # TODO: will recoco guarentee in-order delivery of a sequence of these send requests?
    self._call_later(lambda: self._io_worker.send(message))

  def send(self, data):
    """ send data from the client side. fire and forget. """
    self._send_queue.put(data)

  def has_pending_sends(self):
    ''' called by the "arbitrator" in charge of deferal '''
    return not self._send_queue.empty()

  def permit_receive(self):
    '''
    deque()s the first element of the read queue, and notifies the client
    that there is data to be read.
    
    raises an exception if the read queue is empty
    '''
    data = self._receive_queue.get()
    self._receive_buf += data
    self._client_receive_handler(self)

  def set_receive_handler(self, block):
    ''' Called by client '''
    self._client_receive_handler = block
    
  def peek_receive_buf(self):
    ''' Called by client '''
    return self._receive_buf

  def consume_receive_buf(self, l):
    ''' called by client to consume receive buffer '''
    assert(len(self._receive_buf) >= l)
    self._receive_buf = self._receive_buf[l:]
    
  def io_worker_receive_handler(self, io_worker):
    ''' called from io_worker (recoco thread, after the Select loop pushes onto io_worker) '''
    # Consume everything immediately
    message = io_worker.peek_receive_buf()
    io_worker.consume_receive_buf(len(message))
    # thread-safe queue
    self._receive_queue.put(message)
      
  def has_pending_receives(self):
    ''' called by the "arbitrator" in charge of deferal '''
    return not self._receive_queue.empty()
  
  # ------- Delegation functions. ---------
  # TODO: is there a more pythonic way to implement delegation?
  
  def fileno(self):
    # thread safety shoudn't matter here
    return self._io_worker.fileno()

  def close(self):
    self._call_later(self._io_worker.close)

  @property
  def socket(self):
    return self._io_worker.socket