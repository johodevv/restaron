"""Restore missing PAID order lines from a reviewed, hashed receipt plan.

The default is read-only. --apply creates a backup and checks the entire plan
inside BEGIN IMMEDIATE. Totals and payment records are never rewritten.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


def signature(item):
    return tuple(item.get(key) for key in ('menu_item_id','quantity','unit_price','total_price','portion_size','weight','manual_price'))


def restore(database, plan_path, apply=False, backup_dir=None):
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    database=Path(database).resolve()
    db=sqlite3.connect(database if apply else database.as_uri()+'?mode=ro', uri=not apply, timeout=30)
    db.row_factory=sqlite3.Row
    changes=[]
    try:
        if apply:
            if not backup_dir: raise ValueError('--backup-dir is required for --apply')
            folder=Path(backup_dir).resolve();folder.mkdir(parents=True,exist_ok=True)
            backup=folder/('before_receipt_restore_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite3')
            with sqlite3.connect(backup) as target: db.backup(target)
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
        for entry in plan['orders']:
            pdf=Path(entry['pdf'])
            if hashlib.sha256(pdf.read_bytes()).hexdigest()!=entry['pdf_sha256']:
                raise ValueError('Reviewed PDF changed')
            order=db.execute('SELECT * FROM orders WHERE id=?',(entry['order_id'],)).fetchone()
            archive=db.execute('SELECT * FROM receipt_archives WHERE id=? AND order_id=?',
                               (entry['archive_id'],entry['order_id'])).fetchone()
            if not order or not archive or not order['is_paid'] or archive['receipt_type']!='final_bill':
                raise ValueError('Paid order/archive identity is invalid')
            if order['order_number']!=entry['order_number']:
                raise ValueError('Order identity changed')
            items=json.loads(archive['items_json'])
            if hashlib.sha256(archive['items_json'].encode()).hexdigest()!=entry['items_sha256']:
                raise ValueError('Reviewed archive changed')
            line_sum=round(sum(float(item['total_price']) for item in items),2)
            tender=sum(float(order[name] or 0) for name in ('cash_amount','card_amount','click_amount','debt_amount'))
            if 'advance_amount' in order.keys(): tender+=float(order['advance_amount'] or 0)
            if not (line_sum==archive['subtotal']==order['subtotal'] and archive['total_amount']==order['total']==tender):
                raise ValueError('Receipt and payment totals do not agree')
            wanted=[]
            for item in items:
                candidates=db.execute('''SELECT m.id FROM menu_items m JOIN categories c ON c.id=m.category_id
                    WHERE c.restaurant_id=? AND m.name=? AND m.is_weighted=? AND m.unit=?''',
                    (order['restaurant_id'],item['name'],bool(item.get('is_weighted')),item.get('unit') or 'dona')).fetchall()
                if len(candidates)!=1: raise ValueError('Menu identity is ambiguous or missing')
                wanted.append({'menu_item_id':candidates[0]['id'],'quantity':item['quantity'],
                    'unit_price':item['unit_price'],'total_price':item['total_price'],
                    'portion_size':item.get('size'),'weight':item.get('weight'),'manual_price':item.get('manual_price')})
                columns = {row['name'] for row in db.execute('PRAGMA table_info(order_items)')}
                if 'name_snapshot' in columns:
                    wanted[-1]['name_snapshot'] = item['name']
                if 'prepared_quantity' in columns:
                    wanted[-1]['prepared_quantity'] = 0
            existing=[dict(row) for row in db.execute('SELECT * FROM order_items WHERE order_id=?',(order['id'],))]
            current=Counter(signature(item) for item in existing)
            target=Counter(signature(item) for item in wanted)
            if current-target: raise ValueError('Existing lines conflict with the reviewed receipt')
            missing=target-current
            restored=[]
            for item in wanted:
                key=signature(item)
                if not missing[key]: continue
                missing[key]-=1
                restored.append(item)
                if apply:
                    names=list(item)
                    db.execute(f"INSERT INTO order_items(order_id,{','.join(names)},sent_to_kitchen,sent_quantity,is_prepared) VALUES (?,{','.join('?' for _ in names)},0,0,0)",
                               (order['id'],*(item[name] for name in names)))
            if restored and apply:
                evidence={'source_pdf':str(pdf),'pdf_sha256':entry['pdf_sha256'],'archive_id':archive['id'],
                          'restored_rows':restored,'totals_and_payments_unchanged':True,'fulfilment_history':'unknown'}
                db.execute("INSERT INTO audit_logs(restaurant_id,user_name,user_role,action,entity_type,entity_id,details) VALUES (?,?,?,?,?,?,?)",
                    (order['restaurant_id'],'Authorized receipt recovery','maintenance','historical_lines_restored','order',str(order['id']),json.dumps(evidence)))
            changes.append({'order_id':order['id'],'restored_row_count':len(restored),'restored_total':sum(item['total_price'] for item in restored),'total':order['total']})
        if apply: db.commit()
        return {'applied':apply,'changes':changes, 'backup':str(backup) if apply else None}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True)
    parser.add_argument('--plan',required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--backup-dir')
    args=parser.parse_args()
    print(json.dumps(restore(args.database,args.plan,args.apply,args.backup_dir),indent=2))
