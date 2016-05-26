from celery import Celery

__all__ = ['add', 'running']
_app = Celery('Bigfish.trial.task')
_app.conf.update(
    CELERY_RESULT_BACKEND='redis://:Xinger520@139.129.19.54/0',
    BROKER_URL='redis://:Xinger520@139.129.19.54/0',
)


def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton


@_app.task
def add(x, y):
    return x + y


@_app.task(bind=True)
def running(self):
    return self.request


if __name__ == '__main__':
    r = _app.worker_main()
