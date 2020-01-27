#!/usr/bin/env python3
#
from autopyweb.app import app

if __name__ == "__main__":
    app.run("localhost", port=8000, debug=True, auto_reload=False)
