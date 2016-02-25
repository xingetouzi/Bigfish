from Bigfish.config import MEMORY_DEBUG

__all__ = ['profile']
if MEMORY_DEBUG:
    from memory_profiler import profile
else:
    def profile(func):
        return func
