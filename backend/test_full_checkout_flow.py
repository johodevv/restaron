import urllib.request, json, os
from datetime import datetime

# 1. Login
req = urllib.request.Request('http://localhost:8000/api/v1/auth/login',
    data=json.dumps({'username': 'developer', 'password': 'dev123456'}).encode(),
    headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req, timeout=5)
token = json.loads(res.read())['access_token']

# 2. Get menu item
req_menu = urllib.request.Request('http://localhost:8000/api/v1/menu/full/1',
    headers={'Authorization': f'Bearer {token}'})
menu_res = urllib.request.urlopen(req_menu)
categories = json.loads(menu_res.read())
item_id = 1
for cat in categories:
    for it in cat.get('items', []):
        if not it.get('is_weighted'):
            item_id = it['id']
            break
    if item_id != 1:
        break
print('Selected non-weighted menu item id:', item_id)

# 3. Create dine-in order on table 1
order_data = json.dumps({
    'restaurant_id': 1,
    'table_id': 1,
    'order_type': 'dine_in',
    'customer_name': 'Alisher Navoiy',
    'items': [{'menu_item_id': item_id, 'quantity': 2}]
}).encode()
req_order = urllib.request.Request('http://localhost:8000/api/v1/orders/waiter-create',
    data=order_data,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST')
order_resp = json.loads(urllib.request.urlopen(req_order).read())
order_id = order_resp['id']
print('Created Order:', order_resp['order_number'], 'id:', order_id, 'total:', order_resp['total'])

# 4. Check table 1 status before checkout
req_tbl = urllib.request.Request('http://localhost:8000/api/v1/tables/1',
    headers={'Authorization': f'Bearer {token}'})
tbl_data = json.loads(urllib.request.urlopen(req_tbl).read())
print('Table 1 status BEFORE checkout:', tbl_data.get('status'))

# 5. Checkout order
checkout_data = json.dumps({
    'payment_method': 'cash',
    'cash_amount': order_resp['total'],
    'print_receipt': False
}).encode()
req_checkout = urllib.request.Request(f'http://localhost:8000/api/v1/orders/{order_id}/checkout',
    data=checkout_data,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST')
chk_resp = json.loads(urllib.request.urlopen(req_checkout).read())
print('Checkout success:', chk_resp.get('success'), '| Total paid:', chk_resp.get('total'))

# 6. Check table 1 status AFTER checkout
tbl_data_after = json.loads(urllib.request.urlopen(req_tbl).read())
print('Table 1 status AFTER checkout:', tbl_data_after.get('status'))

# 7. Check PDF file in archive
today_str = datetime.now().strftime('%Y-%m-%d')
pdf_dir = os.path.join('c:/RestAron/backend/receipts_archive/PDFs', today_str)
print('PDF archive folder exists:', os.path.exists(pdf_dir))
if os.path.exists(pdf_dir):
    files = os.listdir(pdf_dir)
    print('PDF files in archive:', files[-3:])
