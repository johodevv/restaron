"""Archive and cancel explicitly confirmed test orders without deleting rows.

Dry-run by default. This is never a general financial reconciliation command.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid


def _rows(db, sql, args=()):
    return [dict(r) for r in db.execute(sql, args)]


def _write_json(path, payload):
    temporary=path.with_suffix('.pending')
    with temporary.open('w',encoding='utf-8') as output:
        json.dump(payload,output,ensure_ascii=False,indent=2)
        output.flush();os.fsync(output.fileno())
    os.replace(temporary,path)


def repair(database, confirmed_ids, archive_directory, *, apply=False, repair_orphans=False):
    database=Path(database).resolve(strict=True)
    ids=sorted(set(int(i) for i in confirmed_ids))
    if not ids or any(i<=0 for i in ids):
        raise ValueError('Faqat tasdiqlangan test buyurtmalarining IDlarini kiriting')
    placeholders=','.join('?' for _ in ids)
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as source:
        source.row_factory=sqlite3.Row
        selected=_rows(source,f'SELECT * FROM orders WHERE id IN ({placeholders}) ORDER BY id',ids)
        if len(selected)!=len(ids):
            raise ValueError('Tasdiqlangan buyurtmalardan ayrimlari topilmadi')
        if not apply:
            return {'dry_run':True,'confirmed_test_ids':ids,'delete_rows':False,
                'repair_orphan_printer_links':repair_orphans}
        archive=Path(archive_directory).resolve();archive.mkdir(parents=True,exist_ok=True)
        run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
        backup=archive/(run_id+'.db')
        with closing(sqlite3.connect(backup)) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('Zaxira yaxlitligi tekshiruvdan o‘tmadi')
            target.row_factory=sqlite3.Row
            backed_up=_rows(target,f'SELECT * FROM orders WHERE id IN ({placeholders}) ORDER BY id',ids)
    payload={'run_id':run_id,'database':str(database),'backup':str(backup),
        'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),
        'confirmed_test_ids':ids,'applied':False}
    manifest=archive/(run_id+'.json')
    with closing(sqlite3.connect(database,timeout=30)) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        try:
            before=_rows(db,f'SELECT * FROM orders WHERE id IN ({placeholders}) ORDER BY id',ids)
            if before!=backed_up:
                raise ValueError('Buyurtmalar zaxira paytida o‘zgardi; qayta tekshirish kerak')
            for table in ('debts','deposit_movements'):
                if db.execute(f'SELECT COUNT(*) FROM {table} WHERE order_id IN ({placeholders})',ids).fetchone()[0]:
                    raise ValueError('Qarz yoki avans tarixi bor test hisobini alohida ko‘rib chiqish kerak')
            if any((o.get('advance_amount') or 0)!=0 for o in before):
                raise ValueError('Avansi bor hisob uchun alohida yarashtirish kerak')
            test_jobs=_rows(db,f'SELECT * FROM print_jobs WHERE order_id IN ({placeholders})',ids)
            orphans=_rows(db,'SELECT p.* FROM print_jobs p LEFT JOIN orders o ON o.id=p.order_id WHERE p.order_id IS NOT NULL AND o.id IS NULL') if repair_orphans else []
            if any(j['status']=='printing' for j in test_jobs+orphans):
                raise ValueError('Tegishli printer vazifasi hozir bajarilmoqda; keyinroq qayta tekshiring')
            tables=sorted({o['table_id'] for o in before if o['table_id'] is not None})
            payload.update(orders=before, items=_rows(db,f'SELECT * FROM order_items WHERE order_id IN ({placeholders})',ids),
                receipts=_rows(db,f'SELECT * FROM receipt_archives WHERE order_id IN ({placeholders})',ids),
                test_print_jobs=test_jobs,orphan_print_jobs=orphans,
                tables=_rows(db,'SELECT * FROM tables WHERE id IN ('+','.join('?' for _ in tables)+')',tables) if tables else [])
            _write_json(manifest,payload)
            now=datetime.now(timezone.utc).isoformat()
            def cents(value):return float(Decimal(str(value or 0)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
            def log(restaurant_id,action,kind,identity,details):
                db.execute('INSERT INTO audit_logs (restaurant_id,user_name,user_role,action,entity_type,entity_id,details,created_at) VALUES (?,?,?,?,?,?,?,?)',
                    (restaurant_id,'User confirmed test records','system',action,kind,str(identity),json.dumps({'run_id':run_id,**details},ensure_ascii=False),now))
            for order in before:
                subtotal=cents(db.execute('SELECT COALESCE(SUM(total_price),0) FROM order_items WHERE order_id=?',(order['id'],)).fetchone()[0])
                fee=cents(Decimal(str(subtotal))*Decimal(str(order['service_fee_percent'] or 0))/100)
                discount=min(max(0,order['discount'] or 0),subtotal+fee)
                db.execute('''UPDATE orders SET status='CANCELLED', is_paid=0, subtotal=?, service_fee_amount=?,
                    discount=?, total=?, cash_amount=0,card_amount=0,click_amount=0,debt_amount=0,advance_amount=0,
                    call_waiter=0,call_status='COMPLETED',closed_at=?,updated_at=?,version=COALESCE(version,1)+1 WHERE id=?''',
                    (subtotal,fee,discount,cents(subtotal+fee-discount),now,now,order['id']))
                log(order['restaurant_id'],'confirmed_test_order_archived','order',order['id'],{'before':order,'archive':str(manifest)})
            db.execute(f"UPDATE print_jobs SET status='cancelled',last_error='Tasdiqlangan test buyurtmasi; asl holat arxivlangan' WHERE order_id IN ({placeholders}) AND status IN ('pending','uncertain')",ids)
            for job in orphans:
                status='done' if job['status']=='done' else 'cancelled'
                db.execute('UPDATE print_jobs SET order_id=NULL,status=?,alerted=?,last_error=? WHERE id=?',
                    (status,0,f"Eski order_id={job['order_id']} topilmadi. Asl bog‘lanish audit arxivida; avtomatik chop etilmaydi.",job['id']))
                log(job['restaurant_id'],'orphan_print_reference_archived','print_job',job['id'],{'before':job,'archive':str(manifest)})
            for tid in tables:
                db.execute("""UPDATE tables SET status='AVAILABLE', current_pin=NULL,is_unlocked=0 WHERE id=?
                    AND status='OCCUPIED' AND COALESCE(deposit_amount,0)=0 AND NOT EXISTS (
                    SELECT 1 FROM orders o WHERE o.table_id=tables.id AND o.is_paid=0 AND o.status NOT IN ('CANCELLED','PAID'))""",(tid,))
            duplicates=db.execute("SELECT table_id FROM orders WHERE table_id IS NOT NULL AND is_paid=0 AND status NOT IN ('CANCELLED','PAID') GROUP BY table_id HAVING COUNT(*)>1").fetchall()
            if not duplicates:
                db.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_orders_one_open_per_table ON orders(table_id) WHERE table_id IS NOT NULL AND is_paid=0 AND status NOT IN ('CANCELLED','PAID')")
            if repair_orphans and db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Boshqa FK tafovutlari bor; tranzaksiya bekor qilindi')
            db.commit()
        except BaseException:
            db.rollback()
            raise
    payload['applied']=True
    _write_json(manifest,payload)
    return {'applied':True,'test_orders_archived':len(ids),'orphan_links_repaired':len(orphans),
        'backup':str(backup),'manifest':str(manifest),'rows_deleted':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True)
    parser.add_argument('--confirmed-test-ids',required=True)
    parser.add_argument('--archive-directory',required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--repair-orphan-printer-links',action='store_true')
    args=parser.parse_args()
    try:
        result=repair(args.database,args.confirmed_test_ids.split(','),args.archive_directory,
            apply=args.apply,repair_orphans=args.repair_orphan_printer_links)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError,sqlite3.Error) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False))
        return 1


if __name__=='__main__':raise SystemExit(main())
