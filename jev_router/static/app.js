"use strict";
const $ = (id) => document.getElementById(id);
let config = null, controller = null;
const labels = {local_llm:"Local Qwen",retrieve:"Documentation + Qwen",clarify:"Clarification",configuration:"Direct configuration"};
function node(tag, text, cls) { const e = document.createElement(tag); if(text !== undefined)e.textContent=text;if(cls)e.className=cls;return e; }
function message(who, text) { if($("messages").querySelector(".welcome"))$("messages").replaceChildren();const e=node("div",undefined,`message ${who==="MODEL"?"model":"user"}`);e.append(node("span",who,"who"),node("div",text));$("messages").append(e);$("messages").scrollTop=$("messages").scrollHeight;return e; }
function stat(root, label, value){const row=node("div",undefined,"stat");row.append(node("span",label),node("strong",value));root.append(row);}
function inspect(data){
  $("route").textContent=labels[data.route]||data.route;$("reason").textContent=`Policy: ${data.policy_reason.replaceAll("_"," ")}`;
  $("decision").replaceChildren();$("timing").replaceChildren();$("sources").replaceChildren();
  const d=data.decision;
  if(d){stat($("decision"),"Decision source",d.source==="demo"?"DEMO FIXTURE":d.model);stat($("decision"),"Confidence",`${(d.confidence*100).toFixed(1)}%`);stat($("decision"),"Needs context",`${(d.needs_context*100).toFixed(1)}%`);
    for(const [name,p] of Object.entries(d.probabilities)){const label=node("div",undefined,"bar-label");label.append(node("span",name),node("span",`${(p*100).toFixed(1)}%`));const bar=node("progress");bar.max=1;bar.value=p;bar.setAttribute("aria-label",`${name} probability`);$("decision").append(label,bar);}
    $("decision").append(node("p",d.source==="demo"?"These values are deterministic demonstration fixtures.":"Confidence summarizes the model distribution; it does not guarantee a correct answer.","hint"));
  } else stat($("decision"),"Model decision","None");
  for(const [name,ms] of Object.entries(data.timing||{}))stat($("timing"),name.replaceAll("_"," "),`${ms.toFixed(1)} ms`);
  if(data.generation_model)stat($("timing"),"Generation",data.generation_model);
  stat($("timing"),"Estimated Jev cost",data.estimated_jev_cost_usd==null?"Unavailable":`$${data.estimated_jev_cost_usd.toFixed(8)}`);
  for(const source of data.sources||[]){const detail=node("details");detail.append(node("summary",`${source.id} · relevance ${source.relevance.toFixed(2)}/2`),node("pre",source.text));$("sources").append(detail);}
}
function busy(value){$("send").disabled=value;$("stop").hidden=!value;$("clear").disabled=value;$("status").textContent=value?"Deciding and generating…":"Ready";}
async function init(){try{const r=await fetch("/api/config");if(!r.ok)throw Error("Could not load configuration");config=await r.json();$("mode").textContent=config.mode==="live"?"LIVE · Jev API":"OFFLINE DEMO";$("key").disabled=!config.auth_required;$("key").placeholder=config.auth_required?"Use ROUTER_API_KEY from .env":"No key needed in demo mode";$("privacy").textContent=config.mode==="live"?"Live mode sends your question and bundled passages to TypeSafe. Qwen generation uses the configured gateway.":"Offline demo uses rules and fixtures. No Jev or LLM API calls are made.";}catch(e){$("error").hidden=false;$("error").textContent=e.message;}}
$("chat-form").addEventListener("submit",async(e)=>{e.preventDefault();if(controller)return;const question=$("question").value.trim();if(!question)return;$("error").hidden=true;if(!config){$("error").textContent="Configuration unavailable. Reload the page.";$("error").hidden=false;return;}const key=$("key").value.trim().replace(/^Bearer\s+/i,"");if(config.auth_required&&!key){$("error").textContent="Enter the router API key from .env first.";$("error").hidden=false;$("key").focus();return;}message("YOU",question);controller=new AbortController();busy(true);try{const headers={"Content-Type":"application/json"};if(key)headers.Authorization=`Bearer ${key}`;const r=await fetch("/api/chat",{method:"POST",headers,body:JSON.stringify({question,max_tokens:Number($("tokens").value)}),signal:controller.signal});const data=await r.json();if(!r.ok)throw Error(typeof data.detail==="string"?data.detail:`Request failed (${r.status})`);message("MODEL",data.answer);inspect(data);$("question").value="";}catch(error){const text=error.name==="AbortError"?"Request stopped.":error.message;message("MODEL",text);$("error").textContent=text;$("error").hidden=false;$("route").textContent="Request did not complete";$("reason").textContent="No result for this question";$("decision").replaceChildren();$("timing").replaceChildren();$("sources").replaceChildren();}finally{controller=null;busy(false);}});
$("question").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();$("chat-form").requestSubmit();}});
$("stop").addEventListener("click",()=>controller?.abort());
$("clear").addEventListener("click",()=>{$("messages").replaceChildren();$("question").value="";$("error").hidden=true;$("decision").replaceChildren();$("timing").replaceChildren();$("sources").replaceChildren();$("route").textContent="Waiting for a question";$("reason").textContent="Routing results will appear here.";});
$("tokens").addEventListener("input",()=>$("token-value").textContent=$("tokens").value);
document.querySelectorAll("[data-question]").forEach(button=>button.addEventListener("click",()=>{$("question").value=button.dataset.question;$("question").focus();}));
init();
