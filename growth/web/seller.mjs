export function scopeResult({market,size,need}) {
  if (!['US','GB','other'].includes(market)||!['small','large','unknown'].includes(size)||!['structure','mismatch','account','identity'].includes(need)) return {eligible:false,message:'Choose a target, row range and issue first.'};
  if (need==='account'||need==='identity') return {eligible:false,message:'This request is outside the file-diagnosis offer. Do not order it for account recovery, sync, tracking or product-identity verification.'};
  if (need==='mismatch') return {eligible:false,message:'A file check cannot establish live price or stock. Ask about scope before ordering; live-store verification is not included.'};
  if (market==='other'||size!=='small') return {eligible:false,message:'The $29 package is not confirmed for this scope. Ask about the target and original row count before ordering; do not assume a larger package is suitable.'};
  return {eligible:true,message:'Potential fit for the $29 report-only diagnosis. Confirm file format, issue scope and delivery on Upwork before ordering. This is not a diagnosis or acceptance.'};
}

if (typeof document!=='undefined') {
  const el=id=>document.getElementById(id);
  const ids=['market','size','need'];
  const reset=()=>{el('seller-brief').value='';el('copy-seller-brief').disabled=true;el('seller-copy-status').textContent='';el('fit-result').textContent='Selections changed. Check the scope again.';};
  ids.forEach(id=>el(id).addEventListener('change',reset));
  el('check-fit').addEventListener('click',()=>{
    const values=Object.fromEntries(ids.map(id=>[id,el(id).value]));
    const result=scopeResult(values);el('fit-result').textContent=result.message;
    const valid=values.market&&values.size&&values.need;
    el('seller-brief').value=valid?`FeedRescue file-diagnosis scope inquiry\nMarket: ${values.market}\nOriginal rows: ${el('size').selectedOptions[0].textContent}\nIssue: ${el('need').selectedOptions[0].textContent}\nFile format: [add CSV, TSV or Google RSS/Atom XML privately]\nPlease confirm fit before I order. I understand the $29 tier is report-only, up to 100 rows and one hour, with two-day delivery after complete requirements. No Google approval or live-store verification is implied.\nScope guide: ${result.message}`:'';
    el('copy-seller-brief').disabled=!valid;
  });
  el('copy-seller-brief').addEventListener('click',async()=>{
    try {await navigator.clipboard.writeText(el('seller-brief').value);el('seller-copy-status').textContent='Copied. Paste into a private Upwork conversation; nothing was submitted here.';}
    catch {el('seller-copy-status').textContent='Copy was blocked. Select and copy the brief manually; nothing was submitted.';}
  });
}
