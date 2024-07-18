import unittest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "Прогноз погоды" in response.text

def test_get_weather():
    response = client.post("/", data={"city": "Москва"})
    assert response.status_code == 200
    assert "Прогноз для города Москва" in response.text

class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
