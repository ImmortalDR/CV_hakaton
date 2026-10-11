"""Periodic addressed task delivery; no email or external services."""
import argparse
import logging
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .tasks import run_due


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    if args.interval < 1: parser.error('interval must be positive')
    engine = create_engine(os.environ['DATABASE_URL'], pool_pre_ping=True)
    factory = sessionmaker(engine, expire_on_commit=False)
    try:
        while True:
            try:
                count = run_due(factory)
                logging.warning('Task scheduler tick complete: %d plans', count)
            except Exception:
                # Do not log SQL parameters, answers or connection credentials.
                logging.error('Task scheduler tick failed; retrying at next interval')
                if args.once: raise SystemExit(1)
            if args.once: break
            time.sleep(args.interval)
    finally:
        engine.dispose()


if __name__ == '__main__': main()
