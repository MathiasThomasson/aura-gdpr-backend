from app.api.routes.tenants import TenantRegisterPayload

payload = {"name": "tenant1", "email": "owner@tenant1.test", "password": "secret"}
try:
    obj = TenantRegisterPayload(**payload)
    print('OK', obj)
except Exception as e:
    print('ERROR', e)
