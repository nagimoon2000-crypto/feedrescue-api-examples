import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {FeedRescueClient} from '../clients/feedrescue-client.mjs';
test('Node SDK hook measures permitted processing only, preserving results and excluding secrets',async()=>{
  let hits=0;
  const server=createServer((request,response)=>{
    hits++;request.resume();
    response.writeHead(200,{'Content-Type':'application/json'});
    response.end(JSON.stringify({data:{analyzed_products:1,issues:[{sku:'private-sku-fixture'}]}}));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try {
    const events=[],origin='http://127.0.0.1:'+server.address().port;
    const api=new FeedRescueClient('private-key-fixture',origin,{onEvent:e=>events.push(e),dataKind:'real'});
    const result=await api.call('products/validate',{processing_consent:true,product:{id:'private-sku-fixture'}});
    assert.equal(result.data.analyzed_products,1);assert.equal(events.length,1);
    assert.equal(events[0].data_kind,'real');
    assert.ok(!/private-key|private-sku/.test(JSON.stringify(events)));
    await api.call('usage');await api.call('products/validate',{processing_consent:false});
    assert.equal(events.length,1);
    const broken=new FeedRescueClient('private-key-fixture',origin,{onEvent:()=>{throw new Error('Fixture failure');}});
    await broken.call('products/validate',{processing_consent:true});
    assert.equal(hits,4); // No telemetry retry of processing.
  } finally {server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});
