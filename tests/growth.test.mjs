import {test} from 'node:test';
import assert from 'node:assert/strict';
import {attribution,createTracker} from '../growth/web/tracking.mjs';

function harness(options={}) {
  const requests=[];
  const transport=async(path,options)=>{requests.push({path,...options,body:JSON.parse(options.body)});return {ok:true};};
  return {requests,tracker:createTracker({enabled:true,transport,...options})};
}
test('no calls before explicit consent; disabled and privacy signal remain off',async()=>{
  for(const options of [{},{enabled:false},{doNotTrack:true}]) {
    const {requests,tracker}=harness(options);
    await tracker.record('sample_run');assert.equal(requests.length,0);
    if(Object.keys(options).length){assert.equal(await tracker.allow(),false);assert.equal(requests.length,0);}
  }
});
test('only known UTM labels survive; full URL, email, token and prototype names are excluded',()=>{
  assert.deepEqual(attribution('?utm_source=pinterest&utm_medium=organic_social&utm_campaign=gtin_tool_20261110'),{source:'pinterest',medium:'organic_social',campaign:'gtin_tool_20261110'});
  for(const search of ['?utm_source=private@example.test&utm_campaign=sk-secret','?utm_source=__proto__&utm_medium=toString&utm_campaign=https://private.test/']) {
    const safe=JSON.stringify(attribution(search));
    assert.ok(!/private|secret|proto|toString/.test(safe));
  }
});
test('consented actions are deduped, schema bounded and money events blocked',async()=>{
  const {requests,tracker}=harness();
  await tracker.allow();await tracker.record('sample_run');await tracker.record('sample_run');
  for(const event of ['paid_started','pilot_request','pilot_approved'])await tracker.record(event);
  assert.deepEqual(requests.map(r=>r.body.event),['docs_view','sample_run']);
  assert.equal(requests[0].credentials,'omit');assert.equal(requests[0].keepalive,true);
  assert.deepEqual(Object.keys(requests[0].body).sort(),['attribution','consent','event','event_id','session_id']);
});
test('withdrawal stops future actions, deletes current session and starts a new opt-in identity',async()=>{
  const {requests,tracker}=harness();
  await tracker.allow();const previous=requests[0].body.session_id;
  assert.equal(await tracker.withdraw(),true);await tracker.record('sample_run');
  assert.equal(requests.at(-1).path,'/growth/forget');
  assert.equal(requests.at(-1).body.session_id,previous);
  await tracker.allow();assert.notEqual(requests.at(-1).body.session_id,previous);
});
test('measurement failures stay failures and do not create retries or block navigation',async()=>{
  let calls=0;const tracker=createTracker({enabled:true,transport:async()=>{calls++;return {ok:false};}});
  await tracker.allow();assert.equal(await tracker.record('sample_run'),false);
  await tracker.record('sample_run');assert.equal(calls,2);
  assert.equal(await tracker.withdraw(),false);
});
