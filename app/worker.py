"""Run with python -m app.worker. Ctrl+C stops the polling worker."""
import logging
import time
from app.operations import dispatch_one, migrate
from app.storage import PaymentStore

def main():
    logging.basicConfig(level=logging.INFO)
    store = PaymentStore()
    migrate(store)
    try:
        while True:
            try:
                if not dispatch_one(store):
                    time.sleep(1)
            except Exception:
                logging.exception('Delivery failed; leased job will be retried')
                time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
