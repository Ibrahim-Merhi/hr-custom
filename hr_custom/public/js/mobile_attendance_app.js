frappe.ready(() => {
  const $ = id => document.getElementById(id);
  const shell = document.querySelector(".attendance-shell");
  const authenticated = shell.dataset.authenticated === "1";
  let coords = null, busy = false, clockOffset = 0, deferredInstall = null;
  let deviceId = localStorage.getItem("hr_mobile_device_id");
  if (!deviceId) { deviceId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`; localStorage.setItem("hr_mobile_device_id", deviceId); }

  function feedback(text, kind="") { const node=$(authenticated?"message":"login-message"); node.textContent=text||""; node.className=`feedback ${kind}`; }
  function api(method,args={}) { return new Promise((resolve,reject)=>frappe.call({method,args,type:method.endsWith("submit_checkin")?"POST":"GET",callback:r=>resolve(r.message),error:r=>{let text=__("Request failed.");try{const messages=JSON.parse(r._server_messages||"[]");if(messages.length)text=JSON.parse(messages[0]).message||messages[0];}catch(e){text=r.message||text;}reject(new Error(text));}})); }

  function startClock(serverTime) {
    clockOffset = moment(serverTime).valueOf() - Date.now();
    const render=()=>{const now=moment(Date.now()+clockOffset);$("server-clock").textContent=now.format("HH:mm:ss");$("server-date").textContent=now.format("dddd, D MMMM YYYY");}; render(); setInterval(render,1000);
  }
  function setGreeting(){const h=moment(Date.now()+clockOffset).hour();const word=h<12?__("Good morning"):h<18?__("Good afternoon"):__("Good evening");const current=$("greeting").textContent.split(",").slice(1).join(",").trim();$("greeting").textContent=`${word}${current?`, ${current}`:""}`;}
  function locate(){coords=null;$("action").disabled=true;$("retry").hidden=true;$("location-title").textContent=__("Locating you");$("location").textContent=__("Requesting a fresh GPS position…");if(!window.isSecureContext){feedback(__("GPS requires HTTPS on this device."),"error");$("retry").hidden=false;return;}if(!navigator.geolocation){feedback(__("Location services are not supported by this browser."),"error");return;}navigator.geolocation.getCurrentPosition(p=>{coords=p.coords;$("location-title").textContent=__("Location ready");$("location").textContent=__("Accuracy: {0} meters",[Math.round(coords.accuracy)]);$("action").disabled=false;feedback("");},e=>{const errors={1:__("Location permission was denied. Enable Location for this site in iPhone Settings."),2:__("Your location is currently unavailable."),3:__("The GPS request timed out. Move to an open area and retry.")};$("location-title").textContent=__("Location unavailable");$("location").textContent=errors[e.code]||e.message;$("retry").hidden=false;feedback($("location").textContent,"error");},{enableHighAccuracy:true,timeout:25000,maximumAge:0});}
  async function refresh(){try{const s=await api("hr_custom.api.mobile_attendance.get_status");startClock(s.server_time);setGreeting();$("employee").textContent=`${s.employee_name} · ${s.employee}`;$("branch").textContent=s.branch||__("Not assigned");$("shift").textContent=s.shift_start?`${moment(s.shift_start).format("HH:mm")} – ${moment(s.shift_end).format("HH:mm")}`:__("Flexible / No shift");$("state").textContent=__(s.current_state);$("state-dot").classList.toggle("in",s.current_state==="CHECKED IN");$("action-label").textContent=s.next_action==="IN"?__("CLOCK IN"):__("CLOCK OUT");$("action").classList.toggle("out",s.next_action==="OUT");$("last-checkin").textContent=s.last_checkin?`${s.last_checkin.log_type} · ${moment(s.last_checkin.time).format("HH:mm")}`:__("No action today");locate();}catch(e){feedback(e.message,"error");}}

  if (!authenticated) {
    $("login-form").addEventListener("submit",event=>{event.preventDefault();const button=$("login-button");button.disabled=true;button.textContent=__("Signing in…");frappe.call({type:"POST",url:"/login",args:{cmd:"login",usr:$("login-email").value.trim(),pwd:$("login-password").value},callback:r=>{if(r.message==="Logged In"||r.message==="No App")location.replace("/attendance");else{button.disabled=false;button.textContent=__("Sign In");feedback(__("Unable to sign in."),"error");}},error:()=>{button.disabled=false;button.textContent=__("Sign In");feedback(__("Invalid username or password."),"error");}});});
    return;
  }

  $("retry").onclick=locate;
  $("logout-button").onclick=()=>api("logout").then(()=>location.replace("/attendance"));
  $("action").onclick=async()=>{if(!coords||busy)return;busy=true;$("action").disabled=true;$("action-label").textContent=__("VALIDATING…");feedback(__("Checking GPS accuracy and branch geofence…"));try{const r=await api("hr_custom.api.mobile_attendance.submit_checkin",{latitude:coords.latitude,longitude:coords.longitude,accuracy:coords.accuracy,device_info:navigator.platform,device_id:deviceId});feedback(__("{0} recorded · {1}m from branch · GPS ±{2}m",[r.action,r.distance,r.accuracy]),"success");setTimeout(refresh,900);}catch(e){feedback(e.message,"error");$("action").disabled=false;}finally{busy=false;}};

  window.addEventListener("beforeinstallprompt",event=>{event.preventDefault();deferredInstall=event;$("install-button").classList.remove("is-hidden");});
  const standalone=matchMedia("(display-mode: standalone)").matches||navigator.standalone;
  if(standalone)$("install-button").classList.add("is-hidden");
  $("install-button").onclick=async()=>{if(deferredInstall){deferredInstall.prompt();await deferredInstall.userChoice;deferredInstall=null;$("install-button").classList.add("is-hidden");}else if(/iphone|ipad|ipod/i.test(navigator.userAgent)){$("ios-install-sheet").classList.remove("is-hidden");}else{feedback(__("Use your browser menu and select Install app or Add to Home screen."));}};
  $("sheet-close").onclick=()=>$("ios-install-sheet").classList.add("is-hidden");
  if("serviceWorker" in navigator&&window.isSecureContext)navigator.serviceWorker.register("/attendance-sw.js").catch(()=>{});
  refresh();
});

