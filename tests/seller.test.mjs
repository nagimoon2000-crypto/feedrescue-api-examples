import test from 'node:test';
import assert from 'node:assert/strict';
import {scopeResult} from '../growth/web/seller.mjs';
test('only bounded US/GB structural scope is potentially eligible',()=>{
  for(const market of ['US','GB'])assert.equal(scopeResult({market,size:'small',need:'structure'}).eligible,true);
  for(const size of ['large','unknown'])assert.equal(scopeResult({market:'US',size,need:'structure'}).eligible,false);
  assert.equal(scopeResult({market:'other',size:'small',need:'structure'}).eligible,false);
});
test('live facts, account and ownership tasks cannot be sold as a file diagnosis',()=>{
  for(const need of ['mismatch','account','identity'])assert.equal(scopeResult({market:'US',size:'small',need}).eligible,false);
});
test('missing and unsupported choices cannot imply acceptance',()=>{
  for(const values of [{},{market:'US',size:'small',need:'invent'}, {market:'US',size:'',need:'structure'}])assert.equal(scopeResult(values).eligible,false);
});
