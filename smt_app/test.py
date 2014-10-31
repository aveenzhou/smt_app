'''
Created on 2014-10-31

@author: Administrator
'''
def cache(d,e):
    
    def wrapper(func):
        def inn_wrapper(*args,**kargs):
          
            print d,e
            return func(*args,**kargs)
            
        return inn_wrapper
    
    return wrapper

@cache(1,2)
def test(a,b):
    print a,b
    



test(3,4)



        