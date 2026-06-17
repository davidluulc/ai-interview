from scripts.seed_demo_accounts import build_demo_accounts


def test_build_demo_accounts_uses_project_demo_emails() -> None:
    accounts = build_demo_accounts(password="123456")

    assert accounts[0].email == "d77013643@gmail.com"
    assert accounts[0].username == "david"
    assert accounts[0].role == "user"
    assert accounts[0].password == "123456"
    assert accounts[1].email == "1011569954@qq.com"
    assert accounts[1].username == "admin"
    assert accounts[1].role == "admin"
    assert accounts[1].password == "123456"
