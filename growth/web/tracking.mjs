// No persistent identifiers, full URLs, referrers, product data or third-party SDK.
export const EVENTS = new Set(['docs_view','sample_run','pilot_cta_click','pilot_brief_copied','file_service_click']);
const sources = new Set(['github','pinterest','upwork','search','direct','other']);
const mediums = new Set(['organic_social','referral','organic','direct','other']);
const campaigns = new Set(['gtin_tool_20261110','developer_quickstart']);
export function attribution(search) {
  const p = new URLSearchParams(search);
  return {
    source: p.has('utm_source') ? (sources.has(p.get('utm_source')) ? p.get('utm_source') : 'other') : 'direct',
    medium: p.has('utm_medium') ? (mediums.has(p.get('utm_medium')) ? p.get('utm_medium') : 'other') : 'direct',
    campaign: p.has('utm_campaign') ? (campaigns.has(p.get('utm_campaign')) ? p.get('utm_campaign') : 'unknown') : 'none'
  };
}
export function createTracker({enabled, search='', doNotTrack=false, transport=fetch, randomId=()=>crypto.randomUUID()}) {
  let session=null, active=false, chain=Promise.resolve(), controller=null;
  const attrs=attribution(search);
  const sent=new Set();
  const post=(path, body, signal)=>transport(path,{method:'POST',credentials:'omit',keepalive:true,
    headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal}).then(r=>{
      if(!r.ok) throw new Error('Measurement unavailable');
    });
  return {
    async allow() {
      if(!enabled || doNotTrack || active) return false;
      session=randomId(); active=true; controller=new AbortController();
      await this.record('docs_view');
      return true;
    },
    record(event) {
      if(!active || !EVENTS.has(event) || sent.has(event)) return Promise.resolve(false);
      sent.add(event); // Once per event per memory-only consent session, no retry.
      const id=session, signal=controller.signal;
      const payload={event,event_id:randomId(),session_id:id,consent:true,attribution:attrs};
      chain=chain.catch(()=>{}).then(async()=>{
        if(!active || session!==id) return false;
        try { await post('/growth/events',payload,signal); return true; }
        catch { return false; }
      });
      return chain;
    },
    async withdraw() {
      const old=session;
      active=false; session=null; sent.clear(); controller?.abort();
      await chain.catch(()=>{});
      if(!old) return true;
      try { await post('/growth/forget',{session_id:old}); return true; }
      catch { return false; }
    },
    isActive:()=>active
  };
}
