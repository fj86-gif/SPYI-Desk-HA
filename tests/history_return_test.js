'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('spyi_desk/SPYI_Dashboard.html','utf8');
const start = html.indexOf('// Calculate annualised price returns solely');
const end = html.indexOf('function renderHistoryReturnSuggestion(){',start);
assert(start>=0 && end>start,'Historical CAGR helper must exist');
const ctx = {Date,Math,Number};vm.createContext(ctx);
vm.runInContext(html.slice(start,end),ctx);
const get = ctx.historicalAnnualReturns;
const begin=Date.parse('2021-11-11T12:00:00Z'),finish=Date.parse('2026-11-13T12:00:00Z');
const closes=[];
for(let ms=begin;ms<=finish;ms+=86400000){const day=new Date(ms);if([0,6].includes(day.getUTCDay()))continue;closes.push({date:day.toISOString().slice(0,10),close:10*Math.pow(1.08,(ms-begin)/(86400000*365.2425))});}
const fresh=get(closes,Date.parse('2026-11-16T10:00:00Z'));
for(const years of [1,3,5]){const row=fresh.returns.find(x=>x.years===years);assert(row,'missing '+years+'y');assert(Math.abs(row.rate-8)<.15, 'unexpected CAGR '+row.rate);}
assert(!fresh.stale);assert(get([],Date.parse('2026-11-16T10:00:00Z')).returns.length===0);
assert(get(closes,Date.parse('2027-02-01T10:00:00Z')).stale);
const sparse=get(closes.slice(-50),Date.parse('2026-11-16T10:00:00Z'));
assert.equal(sparse.returns.length,0);
console.log('PASS 1y/3y/5y historical CAGR, missing data, stale data, short history');
