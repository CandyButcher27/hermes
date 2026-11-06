from control import env_get, toggle


def test_toggle_adds_removes_and_keeps_other_lines():
    text = "A=1\nWHATSAPP_READ_CHATS=111@g.us\nB=2\n"
    text = toggle(text, "WHATSAPP_READ_CHATS", "222@lid", True)
    assert env_get(text, "WHATSAPP_READ_CHATS") == ["111@g.us", "222@lid"]
    text = toggle(text, "WHATSAPP_READ_CHATS", "222@lid", True)
    assert env_get(text, "WHATSAPP_READ_CHATS") == ["111@g.us", "222@lid"]
    text = toggle(text, "WHATSAPP_READ_CHATS", "111@g.us", False)
    assert env_get(text, "WHATSAPP_READ_CHATS") == ["222@lid"]
    assert text.startswith("A=1\n") and "B=2" in text


def test_toggle_creates_missing_key():
    text = toggle("A=1", "WHATSAPP_SEND_CHATS", "333@g.us", True)
    assert text == "A=1\nWHATSAPP_SEND_CHATS=333@g.us\n"
