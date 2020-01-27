# -*- coding: utf-8 -*-
#
from .app import app


# Not sure if we still need this check
if __name__ == "__main__":
    app.run("localhost", 8080)
