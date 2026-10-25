import test from 'node:test';
import assert from 'node:assert/strict';
import { receiptLines } from '../src/utils/receiptLines.js';
test('receipt preview highlights only payable totals including a wrapped amount', () => {
  const lines = receiptLines('Таомлар: 100 000\nЖАМИ ТЎЛОВ:\n 110 000\nРаҳмат\n│Номи│Сумма│');
  assert.deepEqual(lines.map(line => line.total), [false, true, true, false, false]);
  assert.equal(lines[4].table, true);
});
