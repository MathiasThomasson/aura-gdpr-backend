from fastapi.testclient import TestClient
from main import app

class Owner:
    def __init__(self, id, tenant_id):
        self.id = id
        self.tenant_id = tenant_id
        self.role = 'owner'

# override to a dummy owner
from app.core.auth import get_current_user
app.dependency_overrides[get_current_user] = lambda: Owner(1, 1)

client = TestClient(app)
resp = client.post('/api/users/', json={'email':'new@t.test','password':'pwd','role':'user'})
print(resp.status_code)
print(resp.text)
