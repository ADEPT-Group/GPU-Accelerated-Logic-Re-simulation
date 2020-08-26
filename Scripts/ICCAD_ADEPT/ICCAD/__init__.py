import time


class Log:
    def __init__(self):
        self.start = time.perf_counter()

    def log(self, level, message):
        t = time.perf_counter() - self.start
        print(f'{t:011.3f} {level} {message}')

    def info(self, message): self.log('-', message)

    def warn(self, message): self.log('W', message)

    def error(self, message): self.log('E', message)


log = Log()


class MockNumba:
    @staticmethod
    def njit(func):
        def inner(*args, **kwargs):
            return func(*args, **kwargs)
        return inner


numba = MockNumba()

