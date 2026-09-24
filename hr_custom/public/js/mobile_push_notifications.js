import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getMessaging, getToken, isSupported, onMessage } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging.js";

const config = {
	projectId: "hrms-c9607",
	appId: "1:1070897371877:web:327fde68828fe1c1d4920c",
	storageBucket: "hrms-c9607.appspot.com",
	apiKey: "AIzaSyAGb3fCLia5j3yNpSYe5Khoq3hlbRTGSpA",
	authDomain: "hrms-c9607.firebaseapp.com",
	messagingSenderId: "1070897371877",
};
const vapidKey = "BLEuzN1ef8q3kE07mCPD7kyHvU__Cg5w60eMqVAPCYcXo2-5AzM5FFIiB00Sn0CvemIe_9h8kz6d-xrQ-zHgCxs";

frappe.ready(async () => {
	const button = document.getElementById("enable-notifications");
	const message = document.getElementById("notification-message");
	if (!button) return;
	const setMessage = (text, error = false) => { message.textContent = text; message.className = `feedback ${error ? "error" : "success"}`; };
	try {
		if (!(await isSupported()) || !("serviceWorker" in navigator)) {
			button.hidden = true; setMessage(__("Locked-screen notifications are not supported by this browser."), true); return;
		}
		const registration = await navigator.serviceWorker.register("/attendance-sw.js");
		const messaging = getMessaging(initializeApp(config));
		onMessage(messaging, (payload) => frappe.show_alert({message: payload.data?.body || payload.notification?.body || __("New HR notification"), indicator: "green"}, 8));
		const stored = localStorage.getItem("firebase_token_hrms");
		const subscribe = async () => {
			const token = await getToken(messaging, {vapidKey, serviceWorkerRegistration: registration});
			const response = await fetch(`/api/method/hr_custom.api.portal_auth.subscribe_portal_push?fcm_token=${encodeURIComponent(token)}&project_name=hrms`, {credentials: "same-origin"});
			if (!response.ok) throw new Error(__("Could not register this phone for notifications."));
			localStorage.setItem("firebase_token_hrms", token);
			window.hrNotificationRequired = false;
			window.dispatchEvent(new CustomEvent("hr-push-ready"));
			button.textContent = __("Locked-screen notifications enabled");
			setMessage(__("This phone is ready to receive HR notifications."));
		};
		if (Notification.permission === "granted") {
			button.textContent = __("Locked-screen notifications enabled");
			if (!stored) await subscribe();
		} else if (Notification.permission === "default") {
			window.hrNotificationRequired = true;
			setMessage(__("Locked-screen notifications are required. Tap the button below to enable them."), true);
			setTimeout(() => document.getElementById("notification-button")?.click(), 650);
		} else {
			setMessage(__("Notifications are blocked. Enable them for this app in phone Settings."), true);
		}
		button.addEventListener("click", async () => {
			button.disabled = true; setMessage(__("Enabling notifications…"));
			try {
				if (/iphone|ipad|ipod/i.test(navigator.userAgent) && !navigator.standalone) throw new Error(__("On iPhone, install this app on the Home Screen first, then enable notifications."));
				const permission = await Notification.requestPermission();
				if (permission !== "granted") throw new Error(__("Notification permission was not granted. Enable it in phone Settings."));
				await subscribe();
			} catch (error) { setMessage(error.message || __("Could not enable notifications."), true); }
			finally { button.disabled = false; }
		});
	} catch (error) { setMessage(error.message || __("Notification service is unavailable."), true); }
});
