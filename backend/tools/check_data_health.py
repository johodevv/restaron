"""Read-only reconciliation inventory; never rewrites unexplained old sales."""
import argparse
import json
from pathlib import Path
import sqlite3


def check_data_health(database):
    path = Path(database).resolve(strict=True)
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        integrity = [row[0] for row in db.execute('PRAGMA integrity_check')]
        foreign_keys = [dict(row) for row in db.execute('PRAGMA foreign_key_check')]
        accounts = [dict(row) for row in db.execute('''
            SELECT o.id, o.table_id, o.status, o.is_paid, o.subtotal, o.total,
                COALESCE((SELECT SUM(i.total_price) FROM order_items i WHERE i.order_id=o.id),0) AS line_sum,
                COALESCE(o.cash_amount,0)+COALESCE(o.card_amount,0)+COALESCE(o.click_amount,0)+
                COALESCE(o.debt_amount,0)+COALESCE(o.advance_amount,0) AS tender
            FROM orders o
            WHERE ABS(COALESCE(o.subtotal,0)-COALESCE((SELECT SUM(i.total_price)
                FROM order_items i WHERE i.order_id=o.id),0)) > 0.01
            OR (o.is_paid=1 AND ABS(COALESCE(o.total,0)-(COALESCE(o.cash_amount,0)+
                COALESCE(o.card_amount,0)+COALESCE(o.click_amount,0)+COALESCE(o.debt_amount,0)+
                COALESCE(o.advance_amount,0))) > 0.01)
            ORDER BY o.id''')]
        duplicates = [dict(row) for row in db.execute('''SELECT table_id, COUNT(*) AS open_orders,
            GROUP_CONCAT(id) AS order_ids FROM orders WHERE table_id IS NOT NULL
            AND is_paid=0 AND UPPER(status) NOT IN ('PAID','CANCELLED')
            GROUP BY table_id HAVING COUNT(*)>1''')]
        debt_links = [dict(row) for row in db.execute('''SELECT d.id, d.order_id, d.amount,
            o.debt_amount, d.restaurant_id FROM debts d JOIN orders o ON o.id=d.order_id
            WHERE d.restaurant_id!=o.restaurant_id OR (o.is_paid=1 AND ABS(d.amount-o.debt_amount)>.01)''')]
        print_states = dict(db.execute('SELECT status,COUNT(*) FROM print_jobs GROUP BY status'))
    result = dict(database=str(path), integrity=integrity, foreign_key_violations=foreign_keys,
        inconsistent_accounts=accounts, duplicate_open_tables=duplicates, inconsistent_debt_links=debt_links,
        print_job_states=print_states)
    result['healthy'] = integrity == ['ok'] and not any((foreign_keys,accounts,duplicates,debt_links))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        result = check_data_health(args.database)
    except (OSError,sqlite3.Error) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False))
        return 1
    text = json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        output = Path(args.output).resolve()
        if output == Path(args.database).resolve():
            parser.error('Hisobot yo‘li baza fayli bilan bir xil bo‘lishi mumkin emas')
        output.write_text(text,encoding='utf-8')
    else:
        print(text)
    return 0 if result['healthy'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
