#!/usr/bin/env python

import os
import subprocess
import sys
from contextlib import contextmanager

import click


@contextmanager
def run_gunicorn():
    """Start a gunicorn server in background and kill it on context leave"""
    print("Starting gunicorn server...")
    p = subprocess.Popen(["gunicorn", "-w", "4", "flirror:create_app()"])
    try:
        yield p
    finally:
        print("Killing gunicorn server...")
        p.terminate()
        print("Killed gunicorn server")


def create_test_database():
    # Let tox define where we find the database script
    test_db_script = os.environ.get("TEST_DB_SCRIPT")

    print("Creating test database...")
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


@click.command()
@click.argument(
    "backstop_command",
    default="test",
)
def backstop(backstop_command):

    create_test_database()

    # Although I don't like flags, it's the simplest way to get an overall
    # return code. When we use a return 1 in the except block of the Backstop
    # JS command, we would have to pass it through the contextmanager as it is
    # intented to catch any exception and always do it's cleanup.
    failed = False
    with run_gunicorn():
        print("Running Backstop JS...")
        # Run Backstop JS test on the running gunicorn server
        # NOTE (felix): Backstop JS will wait 3 secs so the stocks series JS
        # can load completely.
        try:
            backstop_out = subprocess.check_output(
                ["backstop", backstop_command],
                stderr=subprocess.STDOUT,
                universal_newlines=True,
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

