import urllib.request
import json
import sys

BASE_URL = 'http://127.0.0.1:8000'

def test_system():
    print("=== TEST 1: Login ===")
    req = urllib.request.Request(
        f'{BASE_URL}/api/v1/auth/login',
        data=json.dumps({'username': 'developer', 'password': 'dev123456'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req, timeout=5)
    data = json.loads(res.read())
    token = data['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("Login successful! Token acquired.")

    print("\n=== TEST 2: Find Available Table & Non-Weighted Menu Item ===")
    # Get tables
    req_tables = urllib.request.Request(f'{BASE_URL}/api/v1/tables/?restaurant_id=1', headers=headers)
    tables = json.loads(urllib.request.urlopen(req_tables).read())
    free_table = next((t for t in tables if t.get('status') == 'available'), None)
    if not free_table:
        free_table = tables[0]
    table_id = free_table['id']
    print(f"Using table: {free_table.get('number')} (ID: {table_id})")

    # Get non-weighted item
    req_menu = urllib.request.Request(f'{BASE_URL}/api/v1/menu/full/1', headers=headers)
    cats = json.loads(urllib.request.urlopen(req_menu).read())
    test_item = None
    for c in cats:
        for it in c.get('items', []):
            if not it.get('is_weighted') and it.get('is_available'):
                test_item = it
                break
        if test_item:
            break
    assert test_item, "No available non-weighted item found"
    print(f"Using item: {test_item['name']} (ID: {test_item['id']}, Price: {test_item['price']})")

    print("\n=== TEST 3: Create Order ===")
    order_data = json.dumps({
        'restaurant_id': 1,
        'table_id': table_id,
        'order_type': 'dine_in',
        'customer_name': 'Test Mijoz',
        'items': [{'menu_item_id': test_item['id'], 'quantity': 1}]
    }).encode()
    req_create = urllib.request.Request(
        f'{BASE_URL}/api/v1/orders/waiter-create',
        data=order_data,
        headers=headers,
        method='POST'
    )
    order = json.loads(urllib.request.urlopen(req_create).read())
    order_id = order['id']
    print(f"Order created: ID {order_id}, Number: {order['order_number']}, Items count: {len(order['items'])}")
    assert len(order['items']) == 1
    assert order['items'][0]['quantity'] == 1

    print("\n=== TEST 4: Add SAME item again (Bug 4 verification - line item merging) ===")
    add_data = json.dumps({
        'restaurant_id': 1,
        'items': [{'menu_item_id': test_item['id'], 'quantity': 2}],
        'send_to_kitchen_immediately': False
    }).encode()
    req_add = urllib.request.Request(
        f'{BASE_URL}/api/v1/orders/{order_id}/add-items',
        data=add_data,
        headers=headers,
        method='POST'
    )
    updated_order = json.loads(urllib.request.urlopen(req_add).read())
    print(f"Updated items count: {len(updated_order['items'])}")
    # MUST still be 1 row, but quantity MUST be 3 (1 + 2)
    item_rows = [i for i in updated_order['items'] if i['menu_item_id'] == test_item['id']]
    print(f"Matching item rows: {len(item_rows)}, Quantity: {item_rows[0]['quantity']}")
    assert len(item_rows) == 1, f"Expected 1 merged row, got {len(item_rows)}"
    assert item_rows[0]['quantity'] == 3, f"Expected quantity 3, got {item_rows[0]['quantity']}"
    print("Line item merging works PERFECTLY!")

    print("\n=== TEST 5: Delete Order Item (Bug 3 verification) ===")
    item_to_delete_id = item_rows[0]['id']
    req_del = urllib.request.Request(
        f'{BASE_URL}/api/v1/orders/{order_id}/items/{item_to_delete_id}',
        headers=headers,
        method='DELETE'
    )
    del_res = json.loads(urllib.request.urlopen(req_del).read())
    print("Delete result:", del_res)
    # Check order items
    req_order_check = urllib.request.Request(f'{BASE_URL}/api/v1/orders/{order_id}', headers=headers)
    order_after_del = json.loads(urllib.request.urlopen(req_order_check).read())
    assert len(order_after_del['items']) == 0, "Item should have been deleted"
    print("Item deleted cleanly!")

    print("\n=== TEST 6: Add Item and Checkout ===")
    # Add 1 item so we can checkout
    req_add_final = urllib.request.Request(
        f'{BASE_URL}/api/v1/orders/{order_id}/add-items',
        data=json.dumps({
            'restaurant_id': 1,
            'items': [{'menu_item_id': test_item['id'], 'quantity': 1}],
            'send_to_kitchen_immediately': False
        }).encode(),
        headers=headers,
        method='POST'
    )
    order_final = json.loads(urllib.request.urlopen(req_add_final).read())
    final_total = order_final['total']
    print(f"Final order total to pay: {final_total}")

    checkout_payload = json.dumps({
        'payment_method': 'cash',
        'cash_amount': final_total,
        'print_receipt': False
    }).encode()
    req_checkout = urllib.request.Request(
        f'{BASE_URL}/api/v1/orders/{order_id}/checkout',
        data=checkout_payload,
        headers=headers,
        method='POST'
    )
    chk_res = json.loads(urllib.request.urlopen(req_checkout).read())
    print(f"Checkout success: {chk_res.get('success')}, Total paid: {chk_res.get('total')}")
    assert chk_res.get('success') == True

    # Verify table is now available
    req_tbl_after = urllib.request.Request(f'{BASE_URL}/api/v1/tables/{table_id}', headers=headers)
    tbl_after = json.loads(urllib.request.urlopen(req_tbl_after).read())
    print(f"Table status after checkout: {tbl_after.get('status')}")
    assert tbl_after.get('status') == 'available'

    print("\n==========================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==========================================")

if __name__ == '__main__':
    test_system()
