import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.printer_service import (
    detect_transport,
    is_ip_address,
    get_printer_health,
    check_lan_printer_status,
    check_usb_printer_status,
    print_to_windows_printer,
    _send_raw_bytes,
    PRINT_DOTS_80,
    FONT_A_W,
)
from app.core.security import create_access_token


def test_detect_transport():
    """0: detect_transport IP bo'lsa 'lan', aks holda 'usb' qaytarishi"""
    assert detect_transport("192.168.1.100") == "lan"
    assert detect_transport("192.168.1.100:9100") == "lan"
    assert detect_transport("10.0.0.15:9100") == "lan"
    assert detect_transport("XP-Q80A") == "usb"
    assert detect_transport("POSPrinter POS80") == "usb"
    assert detect_transport("Microsoft Print to PDF") == "usb"
    assert detect_transport("") == "usb"
    assert detect_transport(None) == "usb"


def test_no_heuristic_guessing():
    """5: Printer nomi bo'sh bo'lsa taxmin bilan tanlanmasdan 'Printer sozlanmagan' xatosi chiqishi"""
    res = print_to_windows_printer("Chek matni", printer_name="")
    assert res["success"] is False
    assert res["error"] == "Printer sozlanmagan"

    res_none = print_to_windows_printer("Chek matni", printer_name=None)
    assert res_none["success"] is False
    assert res_none["error"] == "Printer sozlanmagan"

    res_raw = _send_raw_bytes(b"\x00", "")
    assert res_raw["success"] is False
    assert res_raw["error"] == "Printer sozlanmagan"


def test_lan_status_parsing():
    """1: LAN ESC/POS real-time status bitlari (n=1, 2, 4) to'g'ri ajratilishi"""
    # 1. Offline (n=1, bit 3)
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.recv.side_effect = [bytes([0x08]), bytes([0x00]), bytes([0x00])]
        res = check_lan_printer_status("192.168.1.200", 9100)
        assert res["transport"] == "lan"
        assert res["state"] == "offline"
        assert res["detail"] == "Printer offline"

    # 2. Qopqoq ochiq (n=2, bit 2)
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.recv.side_effect = [bytes([0x00]), bytes([0x04]), bytes([0x00])]
        res = check_lan_printer_status("192.168.1.200", 9100)
        assert res["state"] == "cover_open"
        assert res["detail"] == "Qopqoq ochiq"

    # 3. Qog'oz tugagan (n=2, bit 5)
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.recv.side_effect = [bytes([0x00]), bytes([0x20]), bytes([0x00])]
        res = check_lan_printer_status("192.168.1.200", 9100)
        assert res["state"] == "paper_out"
        assert res["detail"] == "Qog'oz tugagan"

    # 4. Javob kelmasa -> 'unknown'
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.recv.side_effect = TimeoutError()
        res = check_lan_printer_status("192.168.1.200", 9100)
        assert res["state"] == "unknown"


def test_usb_status_constants():
    """2: USB Windows spooler konstantalari orqali tekshirish"""
    try:
        import win32print
    except ImportError:
        pytest.skip("win32print mavjud emas")

    with patch("win32print.OpenPrinter", return_value=123), \
         patch("win32print.ClosePrinter"), \
         patch("win32print.EnumJobs", return_value=[{"JobId": 1}]), \
         patch("win32print.GetPrinter", return_value={"Status": win32print.PRINTER_STATUS_PAPER_OUT, "Attributes": 0}):
        res = check_usb_printer_status("XP-Q80A")
        assert res["transport"] == "usb"
        assert res["state"] == "paper_out"
        assert res["detail"] == "Qog'oz tugagan"
        assert res["jobs_in_queue"] == 1


def test_get_printer_health_dispatch():
    """3: get_printer_health LAN yoki USB ga to'g'ri yo'naltirishi"""
    with patch("app.core.printer_service.check_lan_printer_status") as mock_lan:
        mock_lan.return_value = {"transport": "lan", "state": "ok", "detail": "Tayyor"}
        res = get_printer_health("192.168.1.50:9100")
        assert res["transport"] == "lan"
        assert mock_lan.called

    with patch("app.core.printer_service.check_usb_printer_status") as mock_usb:
        mock_usb.return_value = {"transport": "usb", "state": "ok", "detail": "Tayyor", "jobs_in_queue": 0}
        res = get_printer_health("XP-Q80A")
        assert res["transport"] == "usb"
        assert mock_usb.called


def test_receipt_columns_80mm_constant():
    """6: 80mm kenglik formulasi va konstantalarini tekshirish (o'zgartirilmasligi)"""
    assert PRINT_DOTS_80 == 576
    assert FONT_A_W == 12
    # 576 // 12 = 48 belgilar
    assert PRINT_DOTS_80 // FONT_A_W == 48


def test_api_printers_health_and_test_print():
    """3 va 4: GET /receipts/printers/health va POST /receipts/printers/test-print endpointlari"""
    from app.core.security import get_current_user
    from app.models.user import User, UserRole

    mock_admin = User(
        id=1,
        username="admin",
        full_name="Admin",
        role=UserRole.ADMIN,
        restaurant_id=1,
        is_active=True,
        is_approved=True,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_admin

    try:
        client = TestClient(app)

        # 1. Health endpoint
        resp = client.get("/api/v1/receipts/printers/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "printers" in data
        assert data["count"] >= 1

        # 2. Test-print endpoint (bo'sh printer -> 400)
        resp_bad = client.post("/api/v1/receipts/printers/test-print", json={"printer": ""})
        assert resp_bad.status_code == 400

        # 3. Test-print endpoint (valid printer -> 200)
        resp_ok = client.post("/api/v1/receipts/printers/test-print", json={"printer": "XP-Q80A"})
        assert resp_ok.status_code == 200
        res_json = resp_ok.json()
        assert res_json["success"] is True
        assert res_json["status"] == "queued"
        assert res_json["transport"] == "usb"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
