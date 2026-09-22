frappe.ready(() => {
  const byId=id=>document.getElementById(id);
  const authPanel=byId("auth-panel"),appPanel=byId("app-panel"),form=byId("login-form"),button=byId("login-button"),loginMessage=byId("login-message");
  const loggedOutText=__("You are logged out. Please login again.");
  function showLogin(message=loggedOutText){localStorage.removeItem("hr_attendance_logged_in");appPanel.classList.add("is-hidden");authPanel.classList.remove("is-hidden");button.style.display="flex";button.style.alignItems="center";button.style.justifyContent="center";button.disabled=false;button.textContent=__("Sign In");loginMessage.textContent=message;loginMessage.className="feedback error";byId("login-password").value="";document.querySelectorAll(".modal.show,.modal-backdrop").forEach(node=>node.remove());document.body.classList.remove("modal-open");setTimeout(()=>byId("login-username").focus(),50);}
  function permissionText(value){let text="";try{text=typeof value==="string"?value:JSON.stringify(value||"");}catch(e){}return /not permitted|method not allowed|logged out|login again/i.test(text);}
  const nativeMsgprint=frappe.msgprint;
  frappe.msgprint=function(message){if(permissionText(message)||!appPanel||appPanel.classList.contains("is-hidden")){showLogin();return;}return nativeMsgprint.apply(this,arguments);};
  function isSessionError(xhr){
    if(!xhr)return false;
    const text=(xhr.responseText||"").toLowerCase();
    return xhr.status===401 || text.includes("login required") || text.includes("please log in to use mobile attendance") || text.includes('"exc_type":"authenticationerror"');
  }
  window.jQuery(document).ajaxError((event,xhr)=>{if(isSessionError(xhr))showLogin();});
  window.addEventListener("unhandledrejection",event=>{if(/not permitted|method not allowed/i.test(String(event.reason||""))){event.preventDefault();showLogin();}});
  form.addEventListener("submit",async event=>{event.preventDefault();event.stopImmediatePropagation();button.disabled=true;button.textContent=__("Signing in…");loginMessage.textContent="";const body=new URLSearchParams({username:byId("login-username").value.trim(),password:byId("login-password").value});try{const response=await fetch("/api/method/hr_custom.api.portal_auth.login",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8","Accept":"application/json"},body});const data=await response.json();if(!response.ok||!data.message?.authenticated)throw new Error(__("Invalid portal username or password."));localStorage.setItem("hr_attendance_logged_in","1");location.replace(`/attendance?login=${Date.now()}`);}catch(error){button.disabled=false;button.textContent=__("Sign In");loginMessage.textContent=error.message||__("Invalid portal username or password.");loginMessage.className="feedback error";}},true);
  // Logout is owned by mobile_attendance_app.js so the session is ended only
  // after the employee confirms in the app-styled dialog. Binding it here as
  // well would run alongside that handler and make Cancel log the user out.
  if(document.querySelector(".attendance-shell")?.dataset.authenticated==="0")showLogin();
});
