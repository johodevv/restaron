"""Read-only SQLite financial preflight. Does not import the app or migrate data."""
import argparse
import json
import sqlite3
from pathlib import Path


def inspect_database(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    connection.execute('PRAGMA query_only=ON')
    connection.row_factory = sqlite3.Row
    try:
        columns = {r['name'] for r in connection.execute('PRAGMA table_info(orders)')}
        advance = 'COALESCE(o.advance_amount,0)' if 'advance_amount' in columns else '0'
        mismatches = [dict(r) for r in connection.execute(f'''
            SELECT o.id, o.is_paid, o.status, o.subtotal, o.total,
            COALESCE((SELECT SUM(i.total_price) FROM order_items i WHERE i.order_id=o.id),0) line_sum,
            COALESCE(o.cash_amount,0)+COALESCE(o.card_amount,0)+COALESCE(o.click_amount,0)+COALESCE(o.debt_amount,0)+{advance} tender_sum
            FROM orders o WHERE ABS(COALESCE(o.subtotal,0)-(SELECT COALESCE(SUM(i.total_price),0) FROM order_items i WHERE i.order_id=o.id)) > 0.01
            OR (o.is_paid=1 AND ABS(COALESCE(o.total,0)-COALESCE(o.cash_amount,0)-COALESCE(o.card_amount,0)-COALESCE(o.click_amount,0)-COALESCE(o.debt_amount,0)-{advance})>0.01)
        ''')]
        for order in mismatches:
            archives = []
            for row in connection.execute("SELECT id, subtotal, total_amount, items_json FROM receipt_archives WHERE order_id=? AND receipt_type='final_bill'", (order['id'],)):
                try:
                    items = json.loads(row['items_json'] or '[]')
                    line_sum = round(sum(float(item.get('total_price') or 0) for item in items), 2)
                except (TypeError, ValueError):
                    line_sum = None
                archives.append({'archive_id':row['id'], 'subtotal':row['subtotal'], 'total':row['total_amount'], 'line_sum':line_sum})
            order['final_archives'] = archives
        return {
            'database':str(Path(path).resolve()), 'integrity':connection.execute('PRAGMA integrity_check').fetchone()[0],
            'duplicate_open_tables':[dict(r) for r in connection.execute("SELECT table_id, COUNT(*) count FROM orders WHERE table_id IS NOT NULL AND is_paid=0 AND status NOT IN ('PAID','CANCELLED') GROUP BY table_id HAVING COUNT(*)>1")],
            'empty_open_order_ids':[r[0] for r in connection.execute("SELECT o.id FROM orders o WHERE is_paid=0 AND status NOT IN ('PAID','CANCELLED') AND NOT EXISTS(SELECT 1 FROM order_items i WHERE i.order_id=o.id)")],
            'financial_mismatches':mismatches,
            'foreign_key_violations':[list(r) for r in connection.execute('PRAGMA foreign_key_check')],
            'writes_performed':False,
        }
    finally:
        connection.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--output')
    args=parser.parse_args()
    result=inspect_database(args.database)
    serialized=json.dumps(result, indent=2)
    if args.output: Path(args.output).write_text(serialized, encoding='utf-8')
    print(serialized)
