# QueuedPool
Provides capability of creating a pool of workers which will process jobs in a given queue, and the input queue can be updated in another thread.           The workers will process the queue until the pool is deliberately closed. All results are stored in an output queue. It is also possible to change the number of workers in a pool during runtime.
