import sys,unittest,time,threading,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import cpu_jobs

class CPUJobsTests(unittest.TestCase):
 def setUp(self):
  slots=patch.object(cpu_jobs,'_slots',threading.BoundedSemaphore(8));slots.start();self.addCleanup(slots.stop)
 def test_shared_capacity_across_concurrent_batches(self):
  lock=threading.Lock();active=0;peak=0
  def work(value):
   nonlocal active,peak
   with lock:active+=1;peak=max(peak,active)
   time.sleep(.01)
   with lock:active-=1
   return value
  with patch.object(cpu_jobs,'worker_count',return_value=4),patch.object(cpu_jobs,'_slots',threading.BoundedSemaphore(2)):
   from concurrent.futures import ThreadPoolExecutor
   with ThreadPoolExecutor(max_workers=2) as pool:
    jobs=[pool.submit(cpu_jobs.map_ordered,work,list(range(12))) for _ in range(2)]
    for job in jobs:self.assertEqual(job.result(),list(range(12)))
  self.assertEqual(peak,2)

 def test_hardware_limits(self):
  gb=1024**3
  for mode in ('auto','economy','fast','sequential'):
   self.assertEqual(cpu_jobs.worker_count({'cpu_mode':mode},40,cpus=1,memory=16*gb),1)
   self.assertEqual(cpu_jobs.worker_count({'cpu_mode':mode},40,cpus=32,memory=gb),1)
  self.assertEqual(cpu_jobs.worker_count({'cpu_mode':'auto'},40,cpus=32,memory=16*gb),4)
  self.assertEqual(cpu_jobs.worker_count({'cpu_mode':'fast'},40,cpus=32,memory=16*gb),8)
  self.assertEqual(cpu_jobs.worker_count({'cpu_mode':'sequential'},40,cpus=32,memory=16*gb),1)
 def test_parallel_order_and_coordinator_progress(self):
  barrier=threading.Barrier(3);main=threading.get_ident();threads=set();progress=[]
  def work(value):
   threads.add(threading.get_ident());barrier.wait(timeout=3);time.sleep((3-value)*.003);return value*2
  def report(*args):self.assertEqual(threading.get_ident(),main);progress.append(args[0])
  with patch.object(cpu_jobs,'worker_count',return_value=3):result=cpu_jobs.map_ordered(work,[1,2,3],progress=report)
  self.assertEqual(result,[2,4,6]);self.assertEqual(len(threads),3);self.assertEqual(progress,[1,2,3])
 def test_serial_retry_after_parallel_workers_drain(self):
  lock=threading.Lock();active=0;attempts={};retry_active=[]
  def work(value):
   nonlocal active
   with lock:active+=1;attempts[value]=attempts.get(value,0)+1;attempt=attempts[value]
   try:
    if value==1 and attempt==1:raise RuntimeError('tool contention')
    if attempt==2:retry_active.append(active)
    time.sleep(.005);return value
   finally:
    with lock:active-=1
  with patch.object(cpu_jobs,'worker_count',return_value=2):self.assertEqual(cpu_jobs.map_ordered(work,range(5)),list(range(5)))
  self.assertEqual(retry_active,[1]);self.assertEqual(attempts[1],2)
 def test_validation_failure_is_not_retried_and_workers_join(self):
  called=[]
  def work(value):
   called.append(value)
   if value==0:raise ValueError('invalid audio')
   time.sleep(.01)
  with patch.object(cpu_jobs,'worker_count',return_value=2):
   with self.assertRaises(ValueError):cpu_jobs.map_ordered(work,range(20))
  snapshot=list(called);time.sleep(.02);self.assertEqual(called,snapshot);self.assertEqual(called.count(0),1);self.assertLessEqual(len(called),2)
 def test_cancel_drains_workers_without_retry(self):
  class Cancelled(Exception):pass
  event=threading.Event();called=[]
  def check():
   if event.is_set():raise Cancelled()
  def work(value):called.append(value);time.sleep(.01);return value
  def progress(*args):event.set()
  with patch.object(cpu_jobs,'worker_count',return_value=2):
   with self.assertRaises(Cancelled):cpu_jobs.map_ordered(work,range(20),progress=progress,checkpoint=check)
  snapshot=list(called);time.sleep(.02);self.assertEqual(called,snapshot);self.assertLessEqual(len(called),2)
 def test_single_flight_duplicates(self):
  cache=cpu_jobs.SingleFlight();calls=[]
  def build():calls.append(1);time.sleep(.02);return b'encoded'
  with patch.object(cpu_jobs,'worker_count',return_value=4):out=cpu_jobs.map_ordered(lambda _:cache.get('same',build),range(20))
  self.assertEqual(out,[b'encoded']*20);self.assertEqual(calls,[1])
 def test_process_thread_limits_are_local(self):
  args=['ffmpeg.exe','-i','input.wav','output.wav'];before=cpu_jobs.subprocess_options(args)
  with patch.object(cpu_jobs,'worker_count',return_value=2):results=cpu_jobs.map_ordered(lambda _:cpu_jobs.subprocess_options(args),range(2))
  self.assertEqual(cpu_jobs.subprocess_options(args),before)
  self.assertEqual(results[0][1]['env']['OMP_NUM_THREADS'],'1')
  self.assertIn('-filter_threads',results[0][0]);self.assertEqual(args,['ffmpeg.exe','-i','input.wav','output.wav'])

if __name__=='__main__':unittest.main(verbosity=2)
