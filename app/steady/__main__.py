import logging
import sys

from . import config, influx, store
from .server import make_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("steady")

store.clear_running()
if "--demo" in sys.argv:
    from .demo import demo_source
    src = demo_source()
else:
    src = influx
if not config.ANTHROPIC_API_KEY:
    log.warning("ANTHROPIC_API_KEY is empty: reviews will use the plain template")
log.info("serving on :8080")
make_server(src).serve_forever()
