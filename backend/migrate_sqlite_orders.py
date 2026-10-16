import sqlite3

con = sqlite3.connect('c:/RestAron/backend/restaron.db')
cur = con.cursor()

try:
    cur.execute("PRAGMA foreign_keys = OFF;")
    cur.execute("BEGIN TRANSACTION;")
    
    cur.execute("""
    CREATE TABLE orders_new (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
        order_number VARCHAR(20) NOT NULL, 
        restaurant_id INTEGER NOT NULL, 
        table_id INTEGER, 
        waiter_id INTEGER, 
        customer_name VARCHAR(100), 
        customer_note TEXT, 
        status VARCHAR(9) NOT NULL, 
        order_type VARCHAR(50), 
        hall_name VARCHAR(100), 
        kitchen_note TEXT, 
        receipt_note TEXT, 
        subtotal FLOAT, 
        service_fee_percent FLOAT, 
        service_fee_amount FLOAT, 
        discount FLOAT, 
        total FLOAT, 
        is_paid BOOLEAN, 
        payment_method VARCHAR(50), 
        cash_amount FLOAT, 
        card_amount FLOAT, 
        click_amount FLOAT, 
        debt_amount FLOAT, 
        waiter_share_percent FLOAT, 
        waiter_share_amount FLOAT, 
        call_waiter BOOLEAN, 
        call_status VARCHAR(12), 
        call_note VARCHAR(300), 
        created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
        confirmed_at DATETIME, 
        preparing_at DATETIME, 
        ready_at DATETIME, 
        served_at DATETIME, 
        closed_at DATETIME, 
        updated_at DATETIME, 
        customer_phone VARCHAR(30), 
        delivery_address TEXT, 
        FOREIGN KEY(restaurant_id) REFERENCES restaurants (id), 
        FOREIGN KEY(table_id) REFERENCES tables (id), 
        FOREIGN KEY(waiter_id) REFERENCES users (id)
    );
    """)
    
    # Copy data
    cur.execute("""
    INSERT INTO orders_new (
        id, order_number, restaurant_id, table_id, waiter_id, customer_name,
        customer_note, status, order_type, hall_name, kitchen_note, receipt_note,
        subtotal, service_fee_percent, service_fee_amount, discount, total,
        is_paid, payment_method, cash_amount, card_amount, click_amount,
        debt_amount, waiter_share_percent, waiter_share_amount, call_waiter,
        call_status, call_note, created_at, confirmed_at, preparing_at,
        ready_at, served_at, closed_at, updated_at, customer_phone, delivery_address
    )
    SELECT 
        id, order_number, restaurant_id, table_id, waiter_id, customer_name,
        customer_note, status, order_type, hall_name, kitchen_note, receipt_note,
        subtotal, service_fee_percent, service_fee_amount, discount, total,
        is_paid, payment_method, cash_amount, card_amount, click_amount,
        debt_amount, waiter_share_percent, waiter_share_amount, call_waiter,
        call_status, call_note, created_at, confirmed_at, preparing_at,
        ready_at, served_at, closed_at, updated_at, customer_phone, delivery_address
    FROM orders;
    """)
    
    cur.execute("DROP TABLE orders;")
    cur.execute("ALTER TABLE orders_new RENAME TO orders;")
    cur.execute("CREATE UNIQUE INDEX ix_orders_order_number ON orders (order_number);")
    cur.execute("CREATE INDEX ix_orders_id ON orders (id);")
    
    con.commit()
    cur.execute("PRAGMA foreign_keys = ON;")
    print("MIGRATION_SUCCESS")
except Exception as e:
    con.rollback()
    print("MIGRATION_ERROR:", e)
finally:
    con.close()
