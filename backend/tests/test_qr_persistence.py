"""A real process restart must preserve already printed table QR links."""
import json
import os
from pathlib import Path
import subprocess
import sys

BOOT = r'''
import asyncio,json,hashlib
from httpx import AsyncClient,ASGITransport
from sqlalchemy import select
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models import Restaurant,RestaurantSettings,User,Table
from app.core.security import create_access_token

async def main():
 async with app.router.lifespan_context(app):
  async with AsyncSessionLocal() as db:
   if not await db.get(Restaurant,1):
    db.add(Restaurant(id=1,name='QR persistence test',slug='qr-test'))
    db.add(RestaurantSettings(restaurant_id=1,auto_print_kitchen=False,auto_print_customer_bill=False))
    db.add(User(id=1,restaurant_id=1,username='qr_test_admin',full_name='QR test admin',hashed_password='unused',role='admin',is_active=True,is_approved=True))
    await db.commit()
  headers={'Authorization':'Bearer '+create_access_token({'sub':'1','role':'admin'})}
  async with AsyncClient(transport=ASGITransport(app=app),base_url='http://qr-test') as client:
   current=await client.get('/api/v1/tables/?restaurant_id=1',headers=headers)
   if not current.json():
    response=await client.post('/api/v1/tables/',json={'restaurant_id':1,'number':61,'room':'Zal','capacity':6},headers=headers)
    assert response.status_code==201,response.text
   table=(await client.get('/api/v1/tables/?restaurant_id=1',headers=headers)).json()[0]
   token=table['qr_token']
   qr=await client.get('/api/v1/tables/qr-image/'+token,params={'base_url':'https://qr.example.test'})
   assert qr.status_code==200 and qr.content.startswith(bytes([137,80,78,71])),qr.status_code
   scan=await client.get('/api/v1/tables/scan/'+token)
   assert scan.status_code==200,scan.text
   await client.post(f"/api/v1/tables/{table['id']}/lock",json={},headers=headers)
   clear=await client.post(f"/api/v1/tables/{table['id']}/clear",json={},headers=headers)
   assert clear.status_code==200,clear.text
   persisted=(await client.get('/api/v1/tables/?restaurant_id=1',headers=headers)).json()[0]
   assert persisted['qr_token']==token
   print('QR_RESULT='+json.dumps({'id':table['id'],'token':token,'image_hash':hashlib.sha256(qr.content).hexdigest(),'image_url':table['qr_image_url']}),flush=True)
asyncio.run(main())
'''


def test_qr_survives_two_full_app_process_boots(tmp_path):
    database = tmp_path / 'qr_persistence.db'
    env = {**os.environ, 'DATABASE_URL':f'sqlite+aiosqlite:///{database.as_posix()}',
        'SYNC_DATABASE_URL':f'sqlite:///{database.as_posix()}', 'SQLITE_DB_PATH':str(database),
        'SECRET_KEY':'qr-persistence-tests-only-key-20261023', 'AUTO_SEED':'false',
        'UPLOAD_DIR':str(tmp_path/'uploads'), 'PDF_ARCHIVE_DIR':str(tmp_path/'pdf'),
        'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
    results = []
    for _ in range(2):
        process = subprocess.run([sys.executable, '-u', '-c', BOOT], env=env,
            cwd=str(tmp_path), capture_output=True, text=True, encoding='utf-8', timeout=45)
        assert process.returncode == 0, process.stdout + process.stderr
        results.append(json.loads(next(line.removeprefix('QR_RESULT=') for line in process.stdout.splitlines() if line.startswith('QR_RESULT='))))
    assert results[0] == results[1], 'Restart changed an existing table token, image URL or QR pixels'
