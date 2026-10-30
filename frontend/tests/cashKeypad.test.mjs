import test from 'node:test';
import assert from 'node:assert/strict';
import { cashKeypadValue, cashIsInsufficient } from '../src/utils/cashKeypad.js';
test('cash keys compose amounts and preserve fractional input', () => {
  let value = '';
  for (const key of ['2','5','0','00']) value = cashKeypadValue(value,key);
  assert.equal(value,'25000');
  assert.equal(cashKeypadValue('12.5','0'),'12.50');
  assert.equal(cashKeypadValue('12,5','0'),'12.50');
});
test('decimal point, leading zeros, backspace and clear are explicit edits', () => {
  assert.equal(cashKeypadValue('','.'),'0.');
  assert.equal(cashKeypadValue('12.5','.'),'12.5');
  assert.equal(cashKeypadValue('00','5'),'5');
  assert.equal(cashKeypadValue('250000','backspace'),'25000');
  assert.equal(cashKeypadValue('250000','clear'),'');
});
test('unknown keys or malformed values cannot silently alter a cash amount', () => {
  assert.equal(cashKeypadValue('123','submit'),'123');
  assert.equal(cashKeypadValue('1e5','0'),'1e5');
  assert.equal(cashKeypadValue('-5','0'),'-5');
});
test('explicit zero cannot be treated as exact cash; empty and fully discounted totals retain their behavior', () => {
  assert.equal(cashIsInsufficient('0',240800),true);
  assert.equal(cashIsInsufficient('00',240800),true);
  assert.equal(cashIsInsufficient('25000',240800),true);
  assert.equal(cashIsInsufficient('250000',240800),false);
  assert.equal(cashIsInsufficient('',240800),false);
  assert.equal(cashIsInsufficient('0',0),false);
});
