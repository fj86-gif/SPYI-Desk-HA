/* Deterministic ledger/XIRR regression tests; do not require live market data. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('spyi_desk/SPYI_Dashboard.html','utf8');
const from=html.indexOf('function validateTransactionLedger('),to=html.indexOf('function seriesFromHistory()',from);
assert(from>0&&to>from,'Ledger & XIRR functions must exist in dashboard');
const code=html.slice(from,to);
const ctx={state:{tx:[],quote:{asOf:'2026-11-13T17:00:00Z',price:110}},
 dateISO:()=> '2026-11-16',portfolio:()=>({shares:0,value:0}),price:()=>110,Date,Number,Math};
vm.createContext(ctx);vm.runInContext(code,ctx);
const b={id:'b1',date:'2024-11-13',type:'buy',shares:1,price:100,fees:0};
assert.equal(ctx.validateTransactionLedger([b]),null);
assert.match(ctx.validateTransactionLedger([b,{id:'s2',date:'2024-12-13',type:'sell',shares:2,price:110,fees:0}]),/Verkoop/);
assert.match(ctx.validateTransactionLedger([{...b,date:'2024-02-31'}]),/Transactiedatum/);
assert.match(ctx.validateTransactionLedger([{...b,date:'2027-01-02'}]),/Transactiedatum/);
assert.match(ctx.validateTransactionLedger([{...b,price:Infinity}]),/Ongeldige/);
assert.match(ctx.validateTransactionLedger([{...b,fees:-1}]),/Ongeldige/);
assert.match(ctx.validateTransactionLedger([b,{...b}]),/Dubbele/);
ctx.state.tx=[b];ctx.portfolio=()=>({shares:1,value:110});
let result=ctx.xirr();assert(result>4.7&&result<5.1,'Two-year 10% growth has ~4.88% annual XIRR');
ctx.state.tx=[{id:'a',date:'2025-11-13',type:'buy',shares:1,price:100,fees:0}];ctx.portfolio=()=>({shares:1,value:110});
result=ctx.xirr();assert(result>9.9&&result<10.1,'One-year open portfolio XIRR');
ctx.state.tx=[b,{id:'s1',date:'2025-11-13',type:'sell',shares:1,price:110,fees:0}];ctx.portfolio=()=>({shares:0,value:0});
result=ctx.xirr();assert(result>9.9&&result<10.1,'Closed portfolio XIRR');
assert(!html.includes('price:price()||11'),'No fabricated default transaction price');
assert(html.includes('validateTransactionLedger(merged)'),'CSV imports must validate entire timeline');
console.log('PASS ledger validation, XIRR, no invented transaction price');
