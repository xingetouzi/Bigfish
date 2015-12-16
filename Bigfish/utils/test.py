a = 1
def func(a,*b,**d):
    def inner_func(a,*b,**d):
        e = 1
        return(a)
    return(inner_func(a,*b,**d))
b = 1
func(a,1,1,c = b)