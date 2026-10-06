(async()=>{
  const host=document.getElementById('latest-coverage');
  if(!host)return;
  const status=document.getElementById('coverage-status');
  try{
    const response=await fetch('/data/media.json',{cache:'no-cache'});
    if(!response.ok)throw new Error('Feed unavailable');
    const data=await response.json();
    status.textContent=data.updated?'Last refreshed '+new Date(data.updated).toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'})+'. Sources checked every two days.':'Coverage will appear after the first scheduled refresh.';
    if(!data.items.length){host.textContent='More coverage is on its way. Explore the featured video and social channels below.';return;}
    for(const item of data.items.slice(0,30)){
      let url;try{url=new URL(item.url);if(url.protocol!=='https:')continue;}catch{continue;}
      const card=document.createElement('article');card.className='coverage-card';
      if(item.videoId&&/^[A-Za-z0-9_-]{11}$/.test(item.videoId)){
        const frame=document.createElement('iframe');frame.src='https://www.youtube.com/embed/'+item.videoId;frame.title=item.title;frame.loading='lazy';frame.allowFullscreen=true;card.append(frame);
      }
      const source=document.createElement('p');source.className='eyebrow';source.textContent=item.source||'Media coverage';card.append(source);
      const heading=document.createElement('h3');const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener';link.textContent=item.title;heading.append(link);card.append(heading);
      if(item.published){const date=new Date(item.published);if(!Number.isNaN(date.valueOf())){const time=document.createElement('time');time.dateTime=date.toISOString();time.textContent=date.toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'});card.append(time);}}
      host.append(card);
    }
  }catch{status.textContent='Latest coverage is temporarily unavailable. You can still watch the featured video and visit the social channels below.';}
})();
