frappe.ready(() => {
  const el = id => document.getElementById(id);
  let position = null;
  let busy = false;
  let deviceId = localStorage.getItem("hr_mobile_device_id");
  if (!deviceId) {
    deviceId = self.crypto && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem("hr_mobile_device_id", deviceId);
  }
  const message = (text, error=false) => { el("message").textContent=text || ""; el("message").style.color=error?"#c00":""; };
  const call = (method, args={}) => new Promise((resolve, reject) => {
    frappe.call({method, args, type: method.endsWith("submit_checkin") ? "POST" : "GET", callback:r=>resolve(r.message), error:r=>reject(new Error((r && r.message) || __("Request failed."))) });
  });
  function locate() {
    position=null; el("action").disabled=true; el("retry").hidden=true; el("location").textContent=__("Requesting location…");
    if (!navigator.geolocation) { message(__("This browser does not support location services."),true); el("retry").hidden=false; return; }
    navigator.geolocation.getCurrentPosition(p=>{position=p.coords;el("location").textContent=__("Location acquired. Accuracy: {0} meters",[Math.round(position.accuracy)]);el("action").disabled=false;},e=>{const errors={1:__("Location permission was denied. Enable location access in your browser and try again."),2:__("Location is unavailable."),3:__("GPS request timed out.")};message(errors[e.code]||e.message,true);el("retry").hidden=false;},{enableHighAccuracy:true,timeout:25000,maximumAge:0});
  }
  async function refresh() {
    try {
      const s=await call("hr_custom.api.mobile_attendance.get_status");
      el("employee").textContent=`${s.employee_name} (${s.employee})`; el("branch").textContent=s.branch;
      el("state").textContent=__(s.current_state); el("action").textContent=s.next_action==="IN"?__("CHECK IN"):__("CHECK OUT");
      el("last-checkin").textContent=s.last_checkin?__("Last action: {0} at {1}",[s.last_checkin.log_type,moment(s.last_checkin.time).format("YYYY-MM-DD HH:mm:ss")]):"";
      locate();
    } catch(e) { message(e.message||__("Unable to load attendance status."),true); }
  }
  el("retry").onclick=locate;
  el("action").onclick=async()=>{if(!position||busy)return;busy=true;el("action").disabled=true;message(__("Checking allowed area…"));try{const r=await call("hr_custom.api.mobile_attendance.submit_checkin",{latitude:position.latitude,longitude:position.longitude,accuracy:position.accuracy,device_info:navigator.platform,device_id:deviceId});message(__("{0} successful. Distance: {1} m; accuracy: {2} m",[r.action,r.distance,r.accuracy]));await refresh();}catch(e){message(e.message||__("Attendance action failed."),true);el("action").disabled=false;}finally{busy=false;}};
  refresh();
});
