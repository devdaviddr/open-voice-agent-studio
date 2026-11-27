"""Write the API's OpenAPI document for TypeScript codegen. Run via `make gen`."""

import json
import sys
from pathlib import Path

from ovas_api.main import app

if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
