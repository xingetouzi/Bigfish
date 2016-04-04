import time


class Timer:
    def __init__(self):
        self.__last_time = time.time()
        self.__record = []

    def time(self, format=''):
        delta_t = time.time() - self.__last_time
        self.__last_time = self.__last_time + delta_t
        s = '%s seconds' % delta_t
        if format:
            result = format.format(s)
        else:
            result = self.__record.append(s)
        self.__record.append(result)
        return result

    def get_record(self):
        return self.__record

    def reset(self):
        self.__last_time = time.time()
        self.__record.clear()


if __name__ == '__main__':
    t = Timer()
    time.sleep(1)
    x = t.time('adfaf{0}')
    print(x)
    print(t.get_record())
