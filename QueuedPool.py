from __future__ import print_function

import multiprocessing
import time


class SafeValue(object):
    """ Thread safe value. Uses locks. 
    
    Source: http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing
    """
    def __init__(self, initval=0):
        self.val = multiprocessing.Value('i', initval)
        self.lock = multiprocessing.Lock()



    def increment(self):
        with self.lock:
            self.val.value += 1



    def decrement(self):
        with self.lock:
            self.val.value -= 1



    def set(self, n):
        with self.lock:
            self.val.value = n



    def value(self):
        with self.lock:
            return self.val.value



class QueuedPool(object):
    """ Provides capability of creating a pool of workers which will process jobs in a given queue, and the 
        input queue can be updated in another thread. 

        The workers will process the queue until the pool is deliberately closed. All results are stored in an 
        output queue. It is also possible to change the number of workers in a pool during runtime.

    Arguments:
        func: [function] Worker function to which the arguments from the queue will be passed

    Keyword arguments:
        cores: [int] Number of CPU cores to use. None by default.

    """
    def __init__(self, func, cores=None):

        # If the cores are not given, use all available cores
        if cores is None:
            cores = multiprocessing.cpu_count()

        if cores is None:
            cores = 1

        self.cores = SafeValue(cores)

        # Initialize queues
        self.input_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()

        self.func = func
        self.pool = None

        self.total_jobs = SafeValue()
        self.active_workers = SafeValue()
        self.kill_workers = multiprocessing.Event()

        # Start the pool with the given parameters - this will wait until the input queue is given jobs
        self.startPool()



    def _workerFunc(self, func):
        """ A wrapper function for the given worker function. Handles the queue operations. """
            
        self.active_workers.increment()

        while True:

            # Get the function arguments (block until available)
            args = self.input_queue.get(True)

            # The 'poison pill' for killing the worker when closing is requested
            if args is None:
                break

            # Call the original worker function and collect results
            result = func(*args)

            # Save the results to an output queue
            self.output_queue.put(result)

            # Exit if exit is requested
            if self.kill_workers.is_set():
                break

        self.active_workers.decrement()


    def startPool(self):
        """ Start the pool with the given worker function and number of cores. """

        # Initialize the pool of workers with the given number of worker cores
        # Comma in the argument list is a must!
        self.pool = multiprocessing.Pool(self.cores.value(), self._workerFunc, (self.func, ))



    def closePool(self):
        """ Wait until all jobs are done and close the pool. """

        if self.pool is not None:

            # Wait until the input queue is empty, then close the pool
            while True:
                
                # If all jobs are done, close the pool
                if self.output_queue.qsize() == self.total_jobs.value():

                    # Insert the 'poison pill' to the queue, to kill all workers
                    for i in range(self.cores.value()):
                        self.input_queue.put(None)


                    # Wait until the pills are 'swallowed'
                    while self.input_queue.qsize():
                        time.sleep(0.1)


                    # Close the pool and wait for all threads to terminate
                    self.pool.close()
                    self.pool.terminate()
                    self.pool.join()

                    return

                else:
                    time.sleep(0.01)



    def updateCoreNumber(self, cores=None):
        """ Update the number of cores/workers used by the pool.

        Arguments:
            cores: [int] Number of CPU cores to use. None by default.

        """

        # Kill the workers
        self.kill_workers.set()

        # Wait until all workers have exited
        while self.active_workers.value() > 0:
            time.sleep(0.1)

        # Join the previous pool
        self.pool.close()
        self.pool.terminate()
        self.pool.join()

        self.kill_workers.clear()

        # If cores were not given, use all available cores
        if cores is None:
            cores = multiprocessing.cpu_count()

        self.cores.set(cores)

        # Init a new pool
        self.startPool()



    def addJob(self, job):
        """ Add a job to the input queue. Job can be a list of arguments for the worker function. If a list is
            not given, the arguments will be wrapped in the list.

        """

        # Track the total number of jobs received
        self.total_jobs.increment()

        if not isinstance(job, list):
            job = [job]

        self.input_queue.put(job)



    def getResults(self):
        """ Get the results from the output queue and store them in a list. The output list will be returned. 
        """

        results = []

        # Get all elements in the output queue
        if not self.output_queue.empty():
            while True:
                try:
                    results.append(self.output_queue.get(False))
                except:
                    break
            

        return results




def exampleWorker(in_str, in_num):
    """ An example worker function. """

    print('Got:', in_str, in_num)

    t1 = time.time()
    while True:
        if time.time() - t1 > 10:
            break


    return in_str + " " + str(in_num) + " X"




if __name__ == "__main__":

    # Initialize the pool with only one core
    workpool = QueuedPool(exampleWorker, cores=1)

    # Give the pool something to do
    for i in range(2):

        workpool.addJob(["hello", i])

        time.sleep(0.1)

        workpool.addJob(["world", i])


    time.sleep(2)

    print('Updating cores...')

    # Use all available cores
    workpool.updateCoreNumber(3)

    print('Adding more jobs...')

    # Give the pool some more work to do
    for i in range(4):
        workpool.addJob(["test1", i])
        time.sleep(0.05)
        workpool.addJob(["test2", i])


    print('Closing the pool...')

    # Wait for everything to finish and close the pool
    workpool.closePool()


    # Print out the results
    results = workpool.getResults()

    print(results)