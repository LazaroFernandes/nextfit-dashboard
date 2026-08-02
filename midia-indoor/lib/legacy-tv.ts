import type { TvBootstrapData } from "./tv-bootstrap";

function escapeHtml(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function safeJson(value: unknown) {
  return JSON.stringify(value).replace(/</g, "\\u003c").replace(/\u2028/g, "\\u2028").replace(/\u2029/g, "\\u2029");
}

function birthdayName(item: TvBootstrapData["birthdays"][number]) {
  if (item.showLastName) return item.name;
  return item.name.trim().split(/\s+/)[0] || item.name;
}

function renderBirthdayItems(data: TvBootstrapData) {
  return data.birthdays.map((item) => {
    const name = birthdayName(item);
    const photo = item.photoUrl
      ? `<img class="birthday-photo" src="${escapeHtml(item.photoUrl)}" alt="">`
      : `<span class="birthday-photo birthday-initial">${escapeHtml(name.charAt(0).toUpperCase())}</span>`;
    return `<div class="birthday-item">${photo}<div class="birthday-copy"><strong>${escapeHtml(name)}</strong>${item.message ? `<small>${escapeHtml(item.message)}</small>` : ""}</div><div class="clear"></div></div>`;
  }).join("");
}

function renderInitialMedia(data: TvBootstrapData) {
  const item = data.media[0];
  if (!item) return `<div class="fallback"><strong>${escapeHtml(data.settings.fallbackTitle)}</strong><span>${escapeHtml(data.settings.fallbackSubtitle)}</span></div>`;
  if (item.type === "VIDEO") return `<video id="media-video" src="${escapeHtml(item.fileUrl)}" autoplay muted playsinline></video>`;
  return `<img id="media-image" src="${escapeHtml(item.fileUrl)}" alt="${escapeHtml(item.name)}">`;
}

export function renderLegacyTvHtml(data: TvBootstrapData, token: string, device: string) {
  const welcome = data.queue[0];
  return `<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>CT Ítalo Vieira - Mídia Indoor</title>
<style>
html,body{width:100%;height:100%;margin:0;padding:0;overflow:hidden;background:#030814;color:#fff;font-family:Arial,Helvetica,sans-serif}
*{-webkit-box-sizing:border-box;box-sizing:border-box}
#screen{position:absolute;left:0;top:0;width:100%;height:100%;overflow:hidden;background:#061027}
#media{position:absolute;left:0;top:0;width:100%;height:100%;display:table;background:#061027;text-align:center}
#media-inner{display:table-cell;width:100%;height:100%;vertical-align:middle;text-align:center}
#media img,#media video{display:inline-block;max-width:100%;max-height:100%;width:auto;height:auto;vertical-align:middle}
.fallback strong,.fallback span{display:block}.fallback strong{font-size:5vw}.fallback span{margin-top:2vh;font-size:2vw;color:#9fb2d9}
#shade{position:absolute;left:0;right:0;bottom:0;height:25%;background:#020714;opacity:.78;filter:alpha(opacity=78)}
#birthday{position:absolute;right:2.2%;top:4%;width:25%;min-height:18%;max-height:69%;overflow:hidden;padding:1.5%;background:#111827;border:3px solid #f8cc4c;-webkit-border-radius:12px;border-radius:12px;-webkit-box-shadow:0 5px 20px #000;box-shadow:0 5px 20px #000}
#birthday h2{margin:0 0 1.4vh;font-size:1.65vw;line-height:1.15;color:#ffd85f;text-transform:uppercase}
.birthday-item{padding:1vh 0;border-top:1px solid #39445a;text-align:left}.birthday-item:first-child{border-top:0}
.birthday-photo{float:left;width:4.3vw;height:4.3vw;margin-right:.8vw;border:2px solid #ffd85f;-webkit-border-radius:50%;border-radius:50%;background:#26334d;object-fit:cover}
.birthday-initial{font-size:2vw;line-height:4.1vw;text-align:center;font-weight:bold}
.birthday-copy{padding-top:.35vh}.birthday-copy strong,.birthday-copy small{display:block}.birthday-copy strong{font-size:1.4vw;line-height:1.15}.birthday-copy small{margin-top:.45vh;font-size:.88vw;color:#dbe5f8;line-height:1.2}.clear{clear:both;height:0}
#welcome{position:absolute;left:3%;bottom:11%;width:65%;padding:2.1% 2.5%;background:#075ac8;border-left:10px solid #f8cc4c;-webkit-border-radius:8px;border-radius:8px;-webkit-box-shadow:0 5px 24px #000;box-shadow:0 5px 24px #000;text-align:left}
#welcome-label{display:block;margin-bottom:.6vh;font-size:1.05vw;letter-spacing:.22em;color:#cfe4ff;text-transform:uppercase}
#welcome-name{display:block;font-size:3.4vw;line-height:1.05}.welcome-message{display:block;margin-top:.8vh;font-size:1.45vw;color:#eaf4ff}
#footer{position:absolute;left:0;right:0;bottom:0;height:8%;padding:1.2% 2.2%;background:#030816;border-top:1px solid #1c3157}
#brand{float:left;font-size:1.25vw;font-weight:bold;letter-spacing:.08em;color:#f8cc4c}#clock{float:right;font-size:1.5vw;font-weight:bold;color:#fff}
.hidden{display:none!important}.paused #media{opacity:.25;filter:alpha(opacity=25)}
</style></head><body>
<div id="screen" class="${data.paused ? "paused" : ""}">
<div id="media"><div id="media-inner">${renderInitialMedia(data)}</div></div><div id="shade"></div>
<div id="birthday" class="${data.birthdays.length ? "" : "hidden"}"><h2>🎉 Aniversariantes do dia</h2><div id="birthday-list">${renderBirthdayItems(data)}</div></div>
<div id="welcome" class="${welcome ? "" : "hidden"}"><span id="welcome-label">Bem-vindo(a) ao CT Ítalo Vieira</span><strong id="welcome-name">${welcome ? escapeHtml(welcome.displayName) : ""}</strong><span id="welcome-message" class="welcome-message">${welcome ? escapeHtml(welcome.message) : ""}</span></div>
<div id="footer"><span id="brand">CT ÍTALO VIEIRA · MÍDIA INDOOR</span><span id="clock"></span><div class="clear"></div></div></div>
<script>
(function(){
var state=${safeJson(data)},token=${safeJson(token)},device=${safeJson(device)},mediaIndex=0,mediaTimer=null,welcomeTimer=null,activeWelcome="";
function byId(id){return document.getElementById(id);}
function esc(value){return String(value==null?"":value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\"/g,"&quot;").replace(/'/g,"&#39;");}
function show(el,visible){if(!el){return;}if(visible){el.className=el.className.replace(/(^|\\s)hidden(?=\\s|$)/g,"");}else if(el.className.indexOf("hidden")<0){el.className=el.className+" hidden";}}
function firstName(item){var value=item.name||"";return item.showLastName?value:value.replace(/^\\s+|\\s+$/g,"").split(/\\s+/)[0];}
function renderMedia(){var box=byId("media-inner"),items=state.media||[],item,duration;if(mediaTimer){window.clearTimeout(mediaTimer);mediaTimer=null;}if(!items.length){box.innerHTML='<div class="fallback"><strong>'+esc(state.settings.fallbackTitle)+'</strong><span>'+esc(state.settings.fallbackSubtitle)+'</span></div>';return;}if(mediaIndex>=items.length){mediaIndex=0;}item=items[mediaIndex];if(item.type==="VIDEO"){box.innerHTML='<video id="media-video" src="'+esc(item.fileUrl)+'" autoplay muted playsinline></video>';}else{box.innerHTML='<img id="media-image" src="'+esc(item.fileUrl)+'" alt="'+esc(item.name)+'">';}duration=(parseInt(item.durationSec,10)||10)*1000;mediaTimer=window.setTimeout(function(){mediaIndex=(mediaIndex+1)%items.length;renderMedia();},duration);}
function renderBirthdays(){var items=state.birthdays||[],html="",i,item,name,photo;for(i=0;i<items.length;i++){item=items[i];name=firstName(item);photo=item.photoUrl?'<img class="birthday-photo" src="'+esc(item.photoUrl)+'" alt="">':'<span class="birthday-photo birthday-initial">'+esc(name.charAt(0).toUpperCase())+'</span>';html+='<div class="birthday-item">'+photo+'<div class="birthday-copy"><strong>'+esc(name)+'</strong>'+(item.message?'<small>'+esc(item.message)+'</small>':'')+'</div><div class="clear"></div></div>';}byId("birthday-list").innerHTML=html;show(byId("birthday"),items.length>0);}
function request(method,url,body,done){var xhr=new XMLHttpRequest();xhr.open(method,url,true);xhr.onreadystatechange=function(){if(xhr.readyState===4&&done){done(xhr);}};if(body){xhr.setRequestHeader("Content-Type","application/json;charset=UTF-8");}xhr.send(body||null);}
function completeWelcome(id){request("POST","/api/tv/queue?token="+encodeURIComponent(token),JSON.stringify({id:id}),function(){activeWelcome="";show(byId("welcome"),false);poll();});}
function renderWelcome(){var items=state.queue||[],item=items[0],duration;if(!item){activeWelcome="";show(byId("welcome"),false);return;}byId("welcome-name").innerHTML=esc(item.displayName);byId("welcome-message").innerHTML=esc(item.message);show(byId("welcome"),true);if(activeWelcome===item.id){return;}activeWelcome=item.id;if(welcomeTimer){window.clearTimeout(welcomeTimer);}duration=items.length>=(parseInt(state.settings.reducedDurationThreshold,10)||4)?state.settings.reducedDurationSec:state.settings.welcomeDurationSec;welcomeTimer=window.setTimeout(function(){completeWelcome(item.id);},(parseInt(duration,10)||8)*1000);}
function renderAll(){byId("screen").className=state.paused?"paused":"";renderBirthdays();renderWelcome();}
function poll(){request("GET","/api/tv/bootstrap?token="+encodeURIComponent(token)+"&device="+encodeURIComponent(device)+"&_="+(new Date().getTime()),null,function(xhr){if(xhr.status>=200&&xhr.status<300){try{var next=JSON.parse(xhr.responseText),mediaChanged=JSON.stringify(next.media||[])!==JSON.stringify(state.media||[]);state=next;if(mediaChanged){mediaIndex=0;renderMedia();}renderAll();}catch(ignore){}}});}
function clock(){var d=new Date(),h=d.getHours(),m=d.getMinutes();byId("clock").innerHTML=(h<10?"0":"")+h+":"+(m<10?"0":"")+m;}
renderAll();clock();window.setInterval(clock,1000);window.setInterval(poll,4000);
})();
</script></body></html>`;
}
