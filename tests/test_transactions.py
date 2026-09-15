def test_create_and_list_transaction(client, test_user):
    response = client.post(
        "/transactions",
        json={"amount": 50.0, "date": "2026-09-01", "type": "expense"},
        headers=test_user,
    )
    assert response.status_code == 201
    
    response = client.get("/transactions", headers=test_user)
    assert response.status_code == 200
    assert len(response.json()) == 1
    
def test_user_cannot_access_another_users_transaction(client):
    client.post("/users", json={"email": "userA@example.com", "password": "password123"})
    login_a = client.post(
        "/auth/login", data={"username": "userA@example.com", "password": "password123"}
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    
    created = client.post(
        "/transactions",
        json={"amount": 20.0, "date": "2026-09-01", "type": "expense"},
        headers=headers_a,
    )
    transaction_id = created.json()["id"]
    
    client.post("/users", json={"email": "userB@example.com", "password": "password123"})
    login_b = client.post(
        "/auth/login", data={"username": "userB@example.com", "password": "password123"}
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    
    response = client.get(f"/transactions/{transaction_id}", headers=headers_b)
    assert response.status_code == 404
    
def test_invalid_transaction_type_rejected(client, test_user):
    response = client.post(
        "/transactions",
        json={"amount": 50.0, "date": "2026-09-01", "type": "banana"},
        headers=test_user, 
    )
    assert response.status_code == 422
    
def test_negative_amount_rejected(client, test_user):
    response = client.post(
        "/transactions",
        json={"amount": -10.0, "date": "2026-09-01", "type": "expense"},
        headers=test_user,
    )
    assert response.status_code == 422