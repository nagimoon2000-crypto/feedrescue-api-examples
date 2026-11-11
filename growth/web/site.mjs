import {createTracker,attribution} from './tracking.mjs';
const byId=id=>document.getElementById(id);
let tracker=createTracker({enabled:false});
let configured=false;
const privateSignal=navigator.globalPrivacyControl===true || navigator.doNotTrack==='1';
const safeLabels=attribution(location.search);
function brief() {
  byId('brief').value=`FeedRescue API pilot inquiry\nPlatform: ${byId('platform').value}\nTarget: US / GB (choose one)\nApproximate SKU count: [add privately]\nChecks needed: [describe without private product data]\nCampaign labels (not verified attribution): ${safeLabels.source} / ${safeLabels.medium} / ${safeLabels.campaign}\nPlease confirm scope, access limits and processing terms.\nI can start with synthetic data; I will not paste API keys or customer records.\nI understand no billing, Google approval or production SLA is implied.`;
}
byId('platform').addEventListener('change',brief); brief();
fetch('/growth/config',{credentials:'omit'}).then(r=>r.ok?r.json():Promise.reject()).then(config=>{
  configured=config.enabled===true && !privateSignal;
  tracker=createTracker({enabled:configured,search:location.search,doNotTrack:privateSignal});
  byId('allow-measurement').disabled=!configured;
  byId('measurement-status').textContent=privateSignal?'Measurement is off because your browser requests privacy.':configured?'Measurement is off. You can optionally allow it for this visit.':'Measurement is unavailable on this deployment; no activity is recorded.';
}).catch(()=>{byId('measurement-status').textContent='Measurement is unavailable; the page still works.';});
byId('allow-measurement').addEventListener('click',async()=>{
  if(!configured)return;
  const allowed=await tracker.allow();
  byId('allow-measurement').disabled=allowed;
  byId('withdraw-measurement').disabled=!allowed;
  byId('measurement-status').textContent=allowed?'Measurement allowed for this visit. Network failures may leave actions unmeasured.':'Measurement remains off.';
});
byId('withdraw-measurement').addEventListener('click',async()=>{
  byId('withdraw-measurement').disabled=true;
  const deleted=await tracker.withdraw();
  byId('allow-measurement').disabled=!configured;
  byId('measurement-status').textContent=deleted?'Measurement stopped; stored actions for this visit were deleted.':'Measurement stopped locally. Server deletion could not be confirmed; records expire within 30 days.';
});
byId('sample-run').addEventListener('click',async()=>{
  const button=byId('sample-run'); button.disabled=true;
  try {
    const response=await fetch('/sample-diagnosis.json',{credentials:'omit'});
    if(!response.ok)throw new Error('Unavailable');
    const sample=await response.json();
    if(sample.synthetic!==true || sample.changes_applied!==false || sample.google_approval_verified!==false || !Array.isArray(sample.data?.issues))throw new Error('Invalid fixture');
    byId('sample-output').textContent=JSON.stringify(sample,null,2);
    byId('sample-output').hidden=false;
    byId('sample-status').textContent='Saved synthetic report loaded. No API processing call or Google approval occurred.';
    void tracker.record('sample_run');
  } catch {byId('sample-status').textContent='The saved fixture could not load. Use the linked documented example. No successful sample run was recorded.';}
  finally{button.disabled=false;}
});
byId('copy-brief').addEventListener('click',async()=>{
  try {
    await navigator.clipboard.writeText(byId('brief').value);
    byId('copy-status').textContent='Copied. Paste into a private conversation; nothing was submitted here.';
    void tracker.record('pilot_brief_copied');
  } catch {byId('copy-status').textContent='Select the brief and copy it manually. No successful copy was recorded.';}
});
byId('pilot-cta').addEventListener('click',()=>{void tracker.record('pilot_cta_click');});
byId('file-cta').addEventListener('click',()=>{void tracker.record('file_service_click');});
