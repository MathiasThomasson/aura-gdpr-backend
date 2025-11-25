from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
resp = client.post('/api/tenants/register', json={'name':'tenant1','email':'owner@tenant1.test','password':'secret'})
print('status', resp.status_code)
try:
    print('json:', resp.json())
except Exception:
    print('text:', resp.text)
