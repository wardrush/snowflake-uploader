def test_login_success(client, login):
    response = login()
    assert response.status_code == 200
    assert b"Logged in successfully." in response.data


def test_login_failure(client):
    response = client.post(
        "/auth/login",
        data={"email": "staff@example.com", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_protected_pages_require_auth(client):
    upload_response = client.get("/upload")
    staff_response = client.get("/staff/submissions")

    assert upload_response.status_code == 302
    assert "/auth/login" in upload_response.headers["Location"]
    assert staff_response.status_code == 302
    assert "/auth/login" in staff_response.headers["Location"]
