from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.post("/test/{id}")
def test(id: str):
    return {"id": id}

client = TestClient(app)
res = client.post("/test/123", json={})
print("STATUS CODE:", res.status_code)
print("RESPONSE:", res.json())
