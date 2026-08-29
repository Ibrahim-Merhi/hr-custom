const CACHE="attendance-shell-v1";
const ASSETS=["/attendance","/assets/hr_custom/js/mobile_attendance_app.js","/assets/hr_custom/attendance-manifest.json","/assets/hr_custom/images/attendance-icon-512.png"];
self.addEventListener("install",event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS.filter(path=>path!=="/attendance"))).then(()=>self.skipWaiting()));});
self.addEventListener("activate",event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));});
self.addEventListener("fetch",event=>{const url=new URL(event.request.url);if(event.request.method!=="GET"||url.pathname.startsWith("/api/")||url.pathname==="/attendance")return;event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request).then(response=>{const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));return response;})));});
