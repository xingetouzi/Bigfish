# -*- coding: utf-8 -*-
class redirect_stderr:
    """Context manager for temporarily redirecting stdout to another file

        # How to send help() to stderr
        with redirect_stdout(sys.stderr):
            help(dir)

        # How to write help() to a file
        with open('help.txt', 'w') as f:
            with redirect_stdout(f):
                help(pow)
    """

    def __init__(self, new_target):
        self._new_target = new_target
        # We use a list of old targets to make this CM re-entrant
        self._old_targets = []

    def __enter__(self):
        self._old_targets.append(sys.stdout)
        sys.stdout = self._new_target
        return self._new_target

    def __exit__(self, exctype, excinst, exctb):
        sys.stdout = self._old_targets.pop()