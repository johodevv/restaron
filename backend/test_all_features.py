import urllib.request, json, os
from datetime import datetime

print("--- STARTING RESTARON COMPREHENSIVE INTEGRATION TEST ---")

# 1. Login
req = urllib.request.Request('http://localhost:8000/api/v1/auth/login',
    data=json.dumps({'username': 'developer', 'password': 'dev123456'}).encode(),
    headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req, timeout=5)
token = json.loads(res.read())['access_token']
print("1. Login: OK")

# 2. Get menu item
req_menu = urllib.request.Request('http://localhost:8000/api/v1/menu/full/1')
cats = json.loads(urllib.request.urlopen(req_menu).read())
menu_id = None
for c in cats:
    if c.get('items'):
        menu_id = c['items'][0]['id']
        break
menu_id = menu_id or 1
print(f"2. Sample menu item: ID={menu_id}")

# 3. Test Takeaway Order
takeaway_payload = {
    'restaurant_id': 1,
    'order_type': 'takeaway',
    'customer_name': 'Botir Qodirov',
    'customer_phone': '+998901234567',
    'items': [{'menu_item_id': menu_id, 'quantity': 1}]
}
req_takeaway = urllib.request.Request('http://localhost:8000/api/v1/orders/waiter-create',
    data=json.dumps(takeaway_payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST')
takeaway_res = json.loads(urllib.request.urlopen(req_takeaway).read())
print(f"3. Takeaway Order Created: #{takeaway_res['order_number']}, Type={takeaway_res['order_type']}, Phone={takeaway_res['customer_phone']}, Table={takeaway_res['table_id']}")
assert takeaway_res['table_id'] is None, "Takeaway order must have table_id=None"
assert takeaway_res['order_type'] == 'takeaway', "order_type must be takeaway"

# 4. Test Delivery Order
delivery_payload = {
    'restaurant_id': 1,
    'order_type': 'delivery',
    'customer_name': 'Zafarbek',
    'customer_phone': '+998991234567',
    'delivery_address': 'Toshkent sh., Yunusobod 4-mavze, 22-uy',
    'items': [{'menu_item_id': menu_id, 'quantity': 2}]
}
req_delivery = urllib.request.Request('http://localhost:8000/api/v1/orders/waiter-create',
    data=json.dumps(delivery_payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST')
delivery_res = json.loads(urllib.request.urlopen(req_delivery).read())
print(f"4. Delivery Order Created: #{delivery_res['order_number']}, Type={delivery_res['order_type']}, Address={delivery_res['delivery_address']}, Table={delivery_res['table_id']}")
assert delivery_res['table_id'] is None, "Delivery order must have table_id=None"
assert delivery_res['delivery_address'] == delivery_payload['delivery_address']

# 5. Test Dine-in Table Order (Table 1)
table_payload = {
    'restaurant_id': 1,
    'table_id': 1,
    'order_type': 'dine_in',
    'customer_name': 'Ulugbek',
    'items': [{'menu_item_id': menu_id, 'quantity': 3}]
}
req_dine = urllib.request.Request('http://localhost:8000/api/v1/orders/waiter-create',
    data=json.dumps(table_payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST')
dine_res = json.loads(urllib.request.urlopen(req_dine).read())
order_id = dine_res['id']
print(f"5. Table 1 Order Created: #{dine_res['order_number']}, Total={dine_res['total']}")

# Check table status -> OCCUPIED
req_tbl = urllib.request.Request('http://localhost:8000/api/v1/tables/1',
    headers={'Authorization': f'Bearer {token}'})
tbl_status = json.loads(urllib.request.urlopen(req_tbl).read())['status']
print(f"   Table 1 status BEFORE checkout: {tbl_status}")
assert tbl_status == 'occupied', "Table 1 must be occupied"

# 6. Checkout Table 1 Order
checkout_payload = {
    'payment_method': 'cash',
    'cash_amount': dine_res['total'],
    'print_receipt': False
}
req_chk = urllib.request.Request(f'http://localhost:8000/api/v1/orders/{order_id}/checkout',
    data=json.dumps(checkout_payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST')
chk_res = json.loads(urllib.request.urlopen(req_chk).read())
print(f"6. Checkout Table 1 Result: Success={chk_res['success']}, Paid={chk_res['order']['is_paid']}")

# Check table status -> AVAILABLE
tbl_status_after = json.loads(urllib.request.urlopen(req_tbl).read())['status']
print(f"   Table 1 status AFTER checkout: {tbl_status_after}")
assert tbl_status_after == 'available', "Table 1 must be freed to available"

# 7. Checkout Delivery Order
chk_del_payload = {
    'payment_method': 'card',
    'card_amount': delivery_res['total'],
    'print_receipt': False
}
del_order_id = delivery_res["id"]
req_chk_del = urllib.request.Request(f'http://localhost:8000/api/v1/orders/{del_order_id}/checkout',
    data=json.dumps(chk_del_payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST')
chk_del_res = json.loads(urllib.request.urlopen(req_chk_del).read())
print(f"7. Checkout Delivery Order: Success={chk_del_res['success']}, Paid={chk_del_res['order']['is_paid']}")

# 8. Check PDF Archive
today_str = datetime.now().strftime('%Y-%m-%d')
pdf_dir = os.path.join('c:/RestAron/backend/receipts_archive/PDFs', today_str)
print(f"8. PDF Directory Check ({pdf_dir}):")
if os.path.exists(pdf_dir):
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    print(f"   Found {len(pdf_files)} PDF files in today's archive: {pdf_files[-2:]}")
    assert len(pdf_files) >= 2, "PDF receipts should be archived"
else:
    raise AssertionError(f"PDF dir not found: {pdf_dir}")

print("--- ALL INTEGRATION TESTS PASSED 100% SUCCESSFULLY! ---")
