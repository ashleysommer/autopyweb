import unittest
from autopyweb.app import app


class TestApp(unittest.TestCase):
    def test_add_post_only(self):
        client = app.test_client
        request, response = client.get("/add")
        assert response.status == 405
        assert b'Error: Method GET not allowed' in response.content

    def test_add_post_no_args(self):
        client = app.test_client
        request, response = client.post("/add")
        assert response.status == 400
        assert b'Missing parameter' in response.content



