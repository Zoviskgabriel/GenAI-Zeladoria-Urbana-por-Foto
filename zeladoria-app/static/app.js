const form=document.querySelector('#report'), result=document.querySelector('#result');
const photo=form.querySelector('[name="photo"]'), cvCanvas=document.querySelector('#cv-canvas');
const cvPreview=document.querySelector('#cv-preview'), cvReview=document.querySelector('#cv-review-label');
const categories={dano_na_pista:'Buraco ou dano na pista',calcada:'Calçada',bueiro:'Bueiro',lixo:'Lixo',iluminacao:'Iluminação',outro:'Outro'};
const statuses={recebido:'Recebido',em_triagem:'Em triagem',encaminhado:'Encaminhado',descartado:'Descartado'};

async function load(){
  const box=document.querySelector('#reports');
  try{
    const r=await fetch('/api/reports');
    const rows=await r.json();
    box.innerHTML=rows.length?rows.map(x=>{
      const cv=x.cv_label?`<div class="meta">Sugestão do detector: ${esc(x.cv_label)} · ${Math.round(Number(x.cv_confidence||0)*100)}% · ${x.cv_reviewed?'revisada':'aguardando revisão'}</div>`:'';
      return `<article class="queue-item"><strong>${esc(categories[x.category]||x.category)}</strong><div>${esc(x.location)}</div><div class="meta">Protocolo ${esc(x.id)} · ${esc(x.created_at)}</div><span class="status">${esc(statuses[x.status]||x.status)}</span>${cv}<img src="/uploads/${encodeURIComponent(x.image)}" alt="Foto enviada para o relato" style="display:block;max-width:100%;max-height:180px;object-fit:cover;border-radius:8px;margin-top:10px"></article>`;
    }).join(''):'<p>Nenhum relato ainda. O primeiro pode ser o seu.</p>';
  }catch{box.innerHTML='<p>Não foi possível carregar a fila.</p>'}
}

function esc(x){return String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

function drawPreview(file,detections=[]){
  const objectUrl=URL.createObjectURL(file), image=new Image();
  image.onload=()=>{
    const scale=Math.min(900/image.naturalWidth,500/image.naturalHeight,1);
    const width=Math.max(1,Math.round(image.naturalWidth*scale)), height=Math.max(1,Math.round(image.naturalHeight*scale));
    cvCanvas.width=width;cvCanvas.height=height;
    const ctx=cvCanvas.getContext('2d');ctx.drawImage(image,0,0,width,height);
    ctx.strokeStyle='#ff2879';ctx.fillStyle='#ff2879';ctx.lineWidth=Math.max(2,3*scale);
    for(const item of detections){
      const b=item.box;if(!b)continue;
      const x=b.x1*scale,y=b.y1*scale,w=(b.x2-b.x1)*scale,h=(b.y2-b.y1)*scale;
      ctx.strokeRect(x,y,w,h);
      const label=`Buraco ${Math.round(Number(item.confidence||0)*100)}%`;
      ctx.font='bold 14px system-ui';const labelWidth=ctx.measureText(label).width+12;
      ctx.fillRect(x,Math.max(0,y-24),labelWidth,22);ctx.fillStyle='#fff';ctx.fillText(label,x+6,Math.max(15,y-8));ctx.fillStyle='#ff2879';
    }
    cvCanvas.hidden=false;URL.revokeObjectURL(objectUrl);
  };
  image.onerror=()=>{URL.revokeObjectURL(objectUrl);cvCanvas.hidden=true};
  image.src=objectUrl;
}

photo.addEventListener('change',async()=>{
  cvCanvas.hidden=true;cvReview.hidden=true;form.elements.cv_reviewed.checked=false;
  const file=photo.files?.[0];
  if(!file){cvPreview.textContent='A sugestão de visão computacional aparecerá quando um modelo estiver instalado.';return}
  cvPreview.textContent='Analisando a foto…';drawPreview(file);
  const body=new FormData();body.append('photo',file);
  try{
    const response=await fetch('/api/cv/predict',{method:'POST',body}), prediction=await response.json();
    if(!response.ok)throw Error(prediction.error||'Não foi possível analisar a imagem.');
    if(!prediction.available){cvPreview.textContent=prediction.message||'Detector indisponível; escolha a categoria manualmente.';return}
    drawPreview(file,prediction.detections||[]);
    cvReview.hidden=false;
    if(prediction.label){cvPreview.textContent=`Sugestão: buraco/dano na pista (${Math.round(prediction.confidence*100)}%). Confira as caixas na foto e confirme ou corrija a categoria.`}
    else{cvPreview.textContent=prediction.message||'Nenhum buraco foi sugerido. Isso não comprova que a via esteja sem danos.'}
  }catch(error){cvPreview.textContent=`Detector indisponível: ${error.message} A categoria manual continua disponível.`}
});

form.addEventListener('submit',async e=>{
  e.preventDefault();result.textContent='Enviando…';
  const button=form.querySelector('button[type="submit"]');button.disabled=true;
  try{
    const response=await fetch('/api/reports',{method:'POST',body:new FormData(form)}), payload=await response.json();
    if(!response.ok)throw Error(payload.error||'Falha ao enviar');
    result.textContent=`${payload.message} Protocolo ${payload.report_id}.`;
    form.reset();cvCanvas.hidden=true;cvReview.hidden=true;cvPreview.textContent='A sugestão de visão computacional aparecerá quando um modelo estiver instalado.';
    await load();
  }catch(error){result.textContent=error.message}
  finally{button.disabled=false}
});

load();
