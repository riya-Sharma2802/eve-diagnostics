SIGNUP = {"email": "a@example.com", "password": "Passw0rd!", "full_name": "A"}


def test_signup_and_login(client):
    r = client.post("/auth/signup", json=SIGNUP)
    assert r.status_code == 201
    assert "hashed_password" not in r.json()

    r = client.post("/auth/login", json={"email": "a@example.com", "password": "Passw0rd!"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_duplicate_email_is_conflict_case_insensitive(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/signup", json={**SIGNUP, "email": "A@Example.com"})
    assert r.status_code == 409


def test_signup_validation(client):
    assert client.post("/auth/signup", json={**SIGNUP, "password": "short"}).status_code == 422
    assert client.post("/auth/signup", json={**SIGNUP, "email": "not-an-email"}).status_code == 422
    assert client.post("/auth/signup", json={"email": "x@example.com"}).status_code == 422


def test_login_wrong_password_and_unknown_user(client):
    client.post("/auth/signup", json=SIGNUP)
    bad_pw = client.post("/auth/login", json={"email": "a@example.com", "password": "wrongpass1"})
    unknown = client.post("/auth/login", json={"email": "zzz@example.com", "password": "wrongpass1"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json() == unknown.json()


def test_protected_route_requires_valid_token(client):
    assert client.get("/bookings/").status_code == 401
    r = client.get("/bookings/", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
