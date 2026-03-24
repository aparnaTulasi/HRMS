import jwt
from config import Config
from datetime import datetime

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJyb2xlIjoiU1VQRVJfQURNSU4iLCJjb21wYW55X2lkIjpudWxsLCJleHAiOjE3NzQ0MjI2OTF9.M_u5L0lGqNRh3dvcBXWcv5wQD68AGQVY4UP7JJULs4k"

try:
    payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
    print(f"Token is VALID. Payload: {payload}")
    exp_time = datetime.fromtimestamp(payload['exp'])
    print(f"Expires at: {exp_time}")
except Exception as e:
    print(f"Token is INVALID: {e}")
