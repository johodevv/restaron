import test from 'node:test';
import assert from 'node:assert/strict';
import { convertWeightedInput, weightedUpdatePayload } from '../src/utils/weightedItem.js';

test('editing the amount updates kilograms and accepts a decimal comma', () => {
  assert.deepEqual(convertWeightedInput({unit_price:50000,quantity:1}, 'price', '65 000'), {price:'65 000',weight:'1.3'});
  assert.deepEqual(convertWeightedInput({unit_price:50000,quantity:1}, 'weight', '1,8'), {price:'90000',weight:'1,8'});
});

test('a row with two portions uses total price and per-portion weight', () => {
  const item = {unit_price:50000,quantity:2};
  assert.deepEqual(convertWeightedInput(item, 'price', '130000'), {price:'130000',weight:'1.3'});
  assert.deepEqual(convertWeightedInput(item, 'weight', '1.8'), {price:'180000',weight:'1.8'});
});

test('only the edited field is saved so rounded kg cannot overwrite an exact amount', () => {
  const item = {unit_price:120000,quantity:1};
  const values = convertWeightedInput(item, 'price', '150001,25');
  assert.equal(values.weight, '1.25');
  assert.deepEqual(weightedUpdatePayload(item, 'price', values.price, values.weight), {price:150001.25});
  assert.deepEqual(weightedUpdatePayload(item, 'weight', 'stale', '1,35'), {weight:1.35});
});

test('incomplete, negative and invalid values cannot silently become a different amount', () => {
  const item = {unit_price:50000,quantity:1};
  for (const value of ['', '-10', '1x', 'Infinity']) assert.throws(()=>weightedUpdatePayload(item,'price',value,''));
  assert.throws(()=>weightedUpdatePayload(item,'weight','','0'));
  assert.throws(()=>weightedUpdatePayload({unit_price:0},'price','50000',''));
  assert.deepEqual(convertWeightedInput(item,'weight',''), {weight:'',price:''});
});
