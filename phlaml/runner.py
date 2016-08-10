""" runner

Runs commands in yaml file

"""

from __future__ import print_function

import argparse
import atexit
import io
from multiprocessing.pool import ThreadPool
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

import termcolor
import yaml

from . import version


def print_lines(lines, prefix, color):
    for line in lines:
        termcolor.cprint(prefix, color, end='')
        print(line, end='')


def run_command(name, command, features, tmpdir, args):
    stdout_path = os.path.join(tmpdir, '{}.stdout'.format(name))
    stderr_path = os.path.join(tmpdir, '{}.stderr'.format(name))

    if args.verbose:
        termcolor.cprint("Running: {}".format(command), 'green')

    with io.open(stdout_path, 'wb') as stdout_writer, \
        io.open(stdout_path, 'rb') as stdout_reader, \
        io.open(stderr_path, 'wb') as stderr_writer, \
        io.open(stderr_path, 'rb') as stderr_reader:

        start_time = time.time()

        process = subprocess.Popen(command, shell=True, executable=args.shell,
                                   stdout=stdout_writer, stderr=stderr_writer)

        def timeout():
            elapsed_time = time.time() - start_time
            process.terminate()
            termcolor.cprint('TIMEOUT ({:0.0f})'.format(elapsed_time), 'red')

        if features.get('timeout') is not None:
            timer = threading.Timer(int(features.get('timeout')), timeout)
            timer.start()

        def print_output():
            print_lines(stdout_reader.readlines(), '| ', 'green')
            print_lines(stderr_reader.readlines(), ': ', 'yellow')

        while process.poll() is None:
            print_output()
            time.sleep(0.1)

        print_output()

    elapsed_time = time.time() - start_time
    termcolor.cprint("{} ({:0.1f}s)".format(
        'FAILED' if process.returncode else 'PASSED',
        elapsed_time),
        'red' if process.returncode else 'green')

    return process.returncode or 0


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(description="{} script runnner".format(__name__),
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', action='store_true', default=False)
    parser.add_argument('--verbose', '-v', action='store_true', default=True)
    parser.add_argument('--shell', default='/bin/bash')
    parser.add_argument('--workers', default=10, type=int, help="Number of workers.")
    parser.add_argument('--timeout', default=300, type=int, help="Seconds for the entire run.")
    parser.add_argument('--output-timeout', default=60, type=int,
                        help="Seconds without output after which a job is considered to have failed.")
    parser.add_argument('file')
    args = parser.parse_args(argv[1:])
    if args.version:
        print(version.VERSION)
        exit(0)

    with open(args.file, 'r') as f:
        items = yaml.load(f.read())

    assert type(items) == list, \
        "Expected top-level object to be a list but got {}".format(type(items))

    tmpdir = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, tmpdir)

    pool = ThreadPool(args.workers)

    def timeout_handler(signal, frame):
        pool.close()
        pool.terminate()
        sys.exit(termcolor.colored("FAILED: Timed out after {} seconds".format(
            args.timeout), 'red'))

    signal.signal(signal.SIGALRM, timeout_handler)

    timer = threading.Timer(args.timeout, os.kill, (os.getpid(), signal.SIGALRM))
    timer.start()

    try:
        name_count = {}
        results = []
        for index, item in enumerate(items):
            if isinstance(item, dict):
                command, features = next(iter(item.items()))
            else:
                command = item
                features = {}

            name = re.search('\w+', command).group(0)

            if name in name_count:
                name_count[name] += 1
                name = '{}_{}'.format(name, name_count[name])
            else:
                name_count[name] = 0

            result = pool.apply_async(run_command, (), (lambda **kwargs: kwargs)(
                name=name, command=command, features=features, tmpdir=tmpdir, args=args))

            results.append(result)
            if not features.get('background'):
                result.get()
        if not all(r.wait() is None and r.successful() and r.get() == 0 for r in results):
            exit(1)
    finally:
        timer.cancel()

if __name__ == "__main__":
    main(sys.argv)
