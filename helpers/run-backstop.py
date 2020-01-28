#!/usr/bin/env python

import os
import subprocess
import sys
from contextlib import contextmanager
from multiprocessing import Process

import click
from flask.cli import DispatchingApp, ScriptInfo
from flask.helpers import get_debug_flag
from freezegun import freeze_time
from werkzeug.serving import run_simple


@contextmanager
def run_flirror_app():
    def _run():
        with freeze_time("2019-11-27 18:50"):
            # See https://github.com/pallets/flask/blob/master/src/flask/cli.py#L829
            debug = get_debug_flag()
            app = DispatchingApp(ScriptInfo().load_app, use_eager_loading=None)
            run_simple(
                "127.0.0.1",
                5000,
                app,
                use_reloader=debug,
                use_debugger=debug,
                threaded=True,
                ssl_context=None,
                extra_files=None,
            )

    print("Starting local flask server")
    p = Process(target=_run)
    p.start()
    try:
        yield p
    finally:
        print("Killing local flask server")
        p.terminate()
        print("Killed local flask server")


def create_test_database():
    # TODO Initialize database in tox env create script
    # --> So we can use the -r option to also get a fresh database together with
    # the tox env

    # Let tox define where we find the database script
    test_db_script = os.environ.get("TEST_DB_SCRIPT")

    # TODO Look up the database location from the test-settings.cfg file
    print(f"Creating test database in path {os.path.abspath('test-database.sqlite')}")
    if os.path.exists("test-database.sqlite"):
        print("Test database file already exists, reusing it")
        # TODO Provide a -f/--force option to recreate the test database file?
        return

    try:
        # NOTE (felix): This command is much more convenient than doing the whole
        # thing in python as we would have to load the sql file, split the
        # file into single sql commands and execute those.
        # TODO (felix): Maybe there is a way to execute a whole sql file
        # directly in python? So far I did not find anything.
        subprocess.check_output(
            f"sqlite3 test-database.sqlite < '{test_db_script}'", shell=True
        )
    except subprocess.CalledProcessError:
        print("Failed to create test database")
        # TODO (felix): Only the main function should directly exit() the script.
        # Otherwise it might be hard to follow where and why the script was exited.
        sys.exit(1)


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("backstop_command", default="test")
@click.argument("backstop_options", nargs=-1, type=click.UNPROCESSED)
def backstop(backstop_command, backstop_options):

    create_test_database()

    cmd = ["backstop", backstop_command]
    if backstop_options is not None:
        cmd.extend(backstop_options)

    # Although I don't like flags, it's the simplest way to get an overall
    # return code. When we use a return 1 in the except block of the Backstop
    # JS command, we would have to pass it through the contextmanager as it is
    # intented to catch any exception and always do it's cleanup.
    failed = False

    with run_flirror_app():
        print("Running Backstop JS...")
        # Run Backstop JS test on the running gunicorn server
        # NOTE (felix): Backstop JS will wait 3 secs so the stocks series JS
        # can load completely.
        try:
            backstop_out = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, universal_newlines=True,
            )
            print(backstop_out)
        except subprocess.CalledProcessError as exc:
            # I don't like flags
            failed = True
            print(f"Backstop JS returned {exc.returncode}")
            # We want to get the Backstop JS output without the traceback
            print(exc.output)

    # In case the Backstop JS command failed, this script should also fail.
    sys.exit(failed)


if __name__ == "__main__":
    backstop()
