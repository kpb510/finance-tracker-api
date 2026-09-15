def test_register_user(client):
    response = client.post("/users", json={"email": "alice@example.com", "password": "password123"})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "password" not in data

def test_register_duplicate_email(client):
    client.post("/users", json={"email": "alice@example.com", "password": "password123"})
    response = client.post("/users", json={"email": "alice@example.com", "password": "password123"})
    assert response.status_code == 400
    
def test_register_short_password_rejected(client):
    response = client.post("/users", json={"email": "bob@example.com", "password": "short"})
    assert response.status_code == 422
    
def test_login_success(client):
    client.post("/users", json={"email": "carol@example.com", "password": "password123"})
    response = client.post(
        "/auth/login",
        data={"username": "carol@example.com", "password": "password123"}
    )
    assert response.status_code == 200 
    assert "access_token" in response.json()
    
def test_login_wrong_password(client):
    client.post("/users", json={"email": "dave@example.com", "password": "password123"})
    response = client.post(
        "/auth/login",
        data={"username": "dave@example.com", "password": "wrongpassword"}, 
    )
    assert response.status_code == 401

def test_protected_endpoint_requires_token(client):
    response = client.get("/transactions")
    assert response.status_code == 401