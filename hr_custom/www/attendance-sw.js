const CACHE="employee-portal-v46";
const ASSETS=["/assets/hr_custom/js/mobile_attendance_app.js?v=50","/assets/hr_custom/js/attendance_session_guard.js?v=9","/assets/hr_custom/attendance-manifest.json?v=4","/assets/hr_custom/images/attendance-icon-192.png?v=3","/assets/hr_custom/images/attendance-icon-512.png?v=3","/assets/hr_custom/images/apple-touch-icon.png?v=3"];
try {
  importScripts("https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js", "https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js");
  firebase.initializeApp({projectId:"hrms-c9607",appId:"1:1070897371877:web:327fde68828fe1c1d4920c",storageBucket:"hrms-c9607.appspot.com",apiKey:"AIzaSyAGb3fCLia5j3yNpSYe5Khoq3hlbRTGSpA",authDomain:"hrms-c9607.firebaseapp.com",messagingSenderId:"1070897371877"});
  firebase.messaging().onBackgroundMessage(payload=>self.registration.showNotification(payload.data?.title||"HR Notification",{body:payload.data?.body||"",icon:payload.data?.notification_icon||"/assets/hr_custom/images/attendance-icon-512.png",data:{url:payload.data?.click_action||"/attendance"}}));
} catch(error) { console.warn("Push notification initialization failed", error); }
self.addEventListener("install",event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener("activate",event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",event=>{
  const url=new URL(event.request.url);
  // Never handle page navigation. The employee PWA must not control the ERP
  // website root or return a null cached response to Safari.
  if(event.request.method!=="GET"||event.request.mode==="navigate"||url.origin!==self.location.origin)return;
  const cacheable=ASSETS.some(asset=>new URL(asset,self.location.origin).href===url.href);
  if(!cacheable)return;
  event.respondWith(fetch(event.request).then(response=>{
    if(response&&response.ok){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(event.request,copy)));}
    return response;
  }).catch(async()=>await caches.match(event.request)||new Response("Asset temporarily unavailable",{status:503,headers:{"Content-Type":"text/plain; charset=utf-8"}})));
});
self.addEventListener("notificationclick",event=>{event.notification.close();event.waitUntil(clients.matchAll({type:"window",includeUncontrolled:true}).then(list=>{const url=event.notification.data?.url||"/attendance";for(const client of list){if("focus" in client)return client.focus();}return clients.openWindow(url);}));});
