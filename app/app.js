/* Media Assets Explorer — Vue 3 App */
const API = 'http://localhost:9621';
const TC = {concept:'#6c8cff',person:'#f472b6',place:'#4ade80',organization:'#fbbf24',
  object:'#a78bfa',event:'#fb923c',technology:'#22d3ee',emotion:'#f87171',
  style:'#c084fc',color:'#34d399',category:'#f59e0b',default:'#94a3b8'};
const {createApp,ref,computed,nextTick}=Vue;
createApp({setup(){
  const activeTab=ref('query'),healthy=ref(false),graphStats=ref({nodes:0,edges:0});
  const query=ref(''),queryMode=ref('hybrid'),queryResult=ref(''),queryError=ref(''),searching=ref(false);
  const lightboxImage=ref(null);
  const graphData=ref({nodes:[],edges:[]}),graphLabel=ref(''),availableLabels=ref([]);
  const loadingGraph=ref(false),selectedNode=ref(null),nodeSearch=ref('');
  let gInst=null,allGD={nodes:[],edges:[]};
  async function checkHealth(){try{const r=await fetch(API+'/health');if(r.ok){healthy.value=true;try{const r2=await fetch(API+'/graphs?label=*&limit=1');if(r2.ok){const d2=await r2.json();graphStats.value={nodes:(d2.nodes||[]).length>0?'1000+':0,edges:(d2.edges||[]).length};}}catch{}}else{healthy.value=false;}}catch{healthy.value=false;}}
  async function fetchStats(){try{const r=await fetch(API+'/graphs?label=*&limit=1000');if(r.ok){const d=await r.json();graphStats.value={nodes:(d.nodes||[]).length,edges:(d.edges||[]).length};}}catch{}}
  async function search(){if(!query.value.trim()||searching.value)return;searching.value=true;queryResult.value='';queryError.value='';
    try{const r=await fetch(API+'/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:query.value,mode:queryMode.value})});
    if(r.ok){const d=await r.json();queryResult.value=d.response||d.result||JSON.stringify(d);}else{queryError.value='HTTP '+r.status+': '+(await r.text());}}catch(e){queryError.value=e.message;}searching.value=false;}
  const renderedResult=computed(()=>{if(!queryResult.value)return '';try{return marked.parse(queryResult.value);}catch{return queryResult.value.replace(/\n/g,'<br>');}});
  const extractedImages=computed(()=>{if(!queryResult.value)return[];const m=queryResult.value.match(/[\w\-]+\.(?:jpg|jpeg|png|webp|gif|bmp|tiff)/gi)||[];return[...new Set(m)];});
  async function fetchLabels(){try{const r=await fetch(API+'/graph/label/list');if(r.ok){const d=await r.json();availableLabels.value=(d.data||d||[]).filter(l=>l&&l!=='*');}}catch{}}
  async function loadGraph(){loadingGraph.value=true;try{const lbl=graphLabel.value||'*';const r=await fetch(API+'/graphs?label='+encodeURIComponent(lbl)+'&limit=1000');if(r.ok){const d=await r.json();allGD={nodes:d.nodes||[],edges:d.edges||[]};graphData.value={...allGD};await nextTick();renderGraph();}}catch(e){console.error(e);}loadingGraph.value=false;}
  function renderGraph(){const el=document.getElementById('graph-canvas');if(!el)return;el.innerHTML='';
    const nodes=graphData.value.nodes.map(n=>({id:n.id,label:n.id,properties:n.properties||{},labels:n.labels||[],color:typeColor(n.properties?.entity_type)}));
    const ids=new Set(nodes.map(n=>n.id));
    const links=graphData.value.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)).map(e=>({source:e.source,target:e.target,label:(e.properties?.description||'').split('<SEP>')[0].slice(0,60)}));
    gInst=ForceGraph()(el).width(el.clientWidth||800).height(el.clientHeight||500).graphData({nodes,links}).nodeColor(n=>n.color).nodeVal(3).nodeLabel(n=>n.id+'\n('+(n.properties?.entity_type||'unknown')+')').linkColor(()=>'rgba(100,120,180,.25)').linkWidth(0.5).linkDirectionalArrowLength(3).backgroundColor('transparent').onNodeClick(n=>{selectedNode.value=n;});}
  function filterNodes(){const t=nodeSearch.value.toLowerCase();if(!t){graphData.value={...allGD};}else{const fn=allGD.nodes.filter(n=>n.id.toLowerCase().includes(t)||(n.properties?.description||'').toLowerCase().includes(t));const ids=new Set(fn.map(n=>n.id));graphData.value={nodes:fn,edges:allGD.edges.filter(e=>ids.has(e.source)&&ids.has(e.target))};}nextTick(()=>renderGraph());}
  function typeColor(type,alpha){const c=TC[(type||'').toLowerCase()]||TC.default;if(alpha!==undefined){const h=c.replace('#','');return'rgba('+parseInt(h.substring(0,2),16)+','+parseInt(h.substring(2,4),16)+','+parseInt(h.substring(4,6),16)+','+alpha+')';}return c;}
  function cleanDesc(d){return d?d.split('<SEP>')[0].slice(0,300):'';}
  function nodeImageFile(node){if(!node?.properties)return null;const s=(node.properties.description||'')+' '+(node.properties.file_path||'')+' '+(node.id||'');const m=s.match(/[\w\-]+\.(?:jpg|jpeg|png|webp|gif)/i);return m?m[0]:null;}
  const selectedNodeNeighbors=computed(()=>{if(!selectedNode.value)return[];const id=selectedNode.value.id,nb=new Set();allGD.edges.forEach(e=>{const s=typeof e.source==='string'?e.source:e.source?.id;const t=typeof e.target==='string'?e.target:e.target?.id;if(s===id)nb.add(t);if(t===id)nb.add(s);});nb.delete(id);return[...nb].slice(0,30);});
  function focusNode(nid){const n=allGD.nodes.find(x=>x.id===nid);if(n)selectedNode.value={...n};}
  checkHealth();fetchLabels();setInterval(checkHealth,30000);
  return{activeTab,healthy,graphStats,query,queryMode,queryResult,queryError,searching,search,renderedResult,extractedImages,lightboxImage,graphData,graphLabel,availableLabels,loadingGraph,selectedNode,nodeSearch,selectedNodeNeighbors,loadGraph,filterNodes,focusNode,typeColor,cleanDesc,nodeImageFile};
}}).mount('#app');
