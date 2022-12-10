from flask_unittest import ClientTestCase

from astrolog.web.app import app


class TestFoo(ClientTestCase):
    app = app

    def test_simple_call(self, client):
        rv = client.get('/hello')
        self.assertStatus(rv, 200)
        self.assertEqual(rv.data.decode(), 'Hello world!')

    # def test_bar_with_client(self, client):
    #     # Use the client here
    #     # Example login request (on a hypothetical app)
    #     rv = client.post('/login', {'username': 'pinkerton', 'password': 'secret_key'})
    #     # Make sure rv is a redirect request to index page
    #     self.assertLocationHeader('http://localhost/')
    #     # Make sure session is set
