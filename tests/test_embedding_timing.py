from last.embedding_timing import event_times

def test_cuda_event_units_and_warmups():
    calls=[]
    class Event:
        def record(self):calls.append('event')
        def synchronize(self):calls.append('end_sync')
        def elapsed_time(self,end):return 250
    values=event_times(lambda:calls.append('embed'),Event,lambda:calls.append('sync'),lambda:None)
    assert values==[.25]*5
    assert calls.count('embed')==7 and calls.count('event')==10 and calls.count('end_sync')==5
