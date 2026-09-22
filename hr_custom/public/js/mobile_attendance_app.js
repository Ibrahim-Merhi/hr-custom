frappe.ready(() => {
	const byId = (id) => document.getElementById(id);
	const updatePortalHeight = () => {
		const height = window.visualViewport ? window.visualViewport.height : window.innerHeight;
		document.documentElement.style.setProperty("--portal-height", `${Math.round(height)}px`);
	};
	updatePortalHeight();
	window.addEventListener("resize", updatePortalHeight, {passive: true});
	window.addEventListener("orientationchange", () => setTimeout(updatePortalHeight, 120), {passive: true});
	if (window.visualViewport) window.visualViewport.addEventListener("resize", updatePortalHeight, {passive: true});
	setTimeout(() => byId("app-splash")?.classList.add("is-ready"), 900);
	const setText = (id, value) => { const node = byId(id); if (node) node.textContent = value ?? ""; };
	const shell = document.querySelector(".attendance-shell");
	const authenticated = shell?.dataset.authenticated === "1";
	const isArabic = (frappe.boot?.lang || "").startsWith("ar");
	const nativeTranslate = window.__;
	const arabicPortalTranslations = {
		"Good morning": "صباح الخير", "Good afternoon": "مساء الخير", "Good evening": "مساء الخير",
		"Not assigned": "غير معيّن", "CHECKED IN": "تم تسجيل الدخول", "CHECKED OUT": "تم تسجيل الخروج",
		"CLOCK IN": "تسجيل الدخول", "CLOCK OUT": "تسجيل الخروج", "No action today": "لا توجد حركة اليوم",
		"Present": "حاضر", "Absent": "غائب", "Abnormal": "غير طبيعي", "Pending": "معلّق", "On Leave": "في إجازة",
		"Approved": "موافق عليه", "Rejected": "مرفوض", "Applied": "تم التطبيق", "Open": "مفتوح",
		"Pending Approver Approval": "بانتظار موافقة المعتمد", "Pending HR Approval": "بانتظار موافقة الموارد البشرية",
		"Abnormal / Pending": "غير طبيعي / معلّق", "Casual Leave": "إجازة عارضة", "Sick Leave": "إجازة مرضية",
		"Male": "ذكر", "Female": "أنثى", "Full-time": "دوام كامل", "Part-time": "دوام جزئي",
		"Employee": "الموظف", "Dates": "التواريخ", "Amount": "المقدار", "Status": "الحالة", "Reason": "السبب",
		"Approval Progress": "مسار الموافقات", "Working Hours": "ساعات العمل", "Punches": "سجلات الدخول والخروج",
		"Correction Requests": "طلبات تصحيح الحضور", "Shift": "الوردية", "Date": "التاريخ",
		"Requested Check In": "وقت الدخول المطلوب", "Requested Check Out": "وقت الخروج المطلوب",
		"No approval steps": "لا توجد مراحل موافقة", "Waiting for HR": "بانتظار الموارد البشرية",
		"Attendance correction": "تصحيح الحضور", "Your approval": "بانتظار موافقتك", "Final HR": "الموافقة النهائية للموارد البشرية",
		"HR Override": "تجاوز الموارد البشرية", "days": "أيام", "remaining": "متبقي", "Used": "مستخدم", "Allocated": "مخصص",
		"Employee Details": "بيانات الموظف", "Employee Name": "اسم الموظف", "Gender": "الجنس",
		"Date of Birth": "تاريخ الميلاد", "Date of Joining": "تاريخ الالتحاق", "Employment Type": "نوع التوظيف",
		"Company Information": "معلومات الشركة", "Company": "الشركة", "Department": "القسم", "Designation": "المسمى الوظيفي",
		"Branch": "الفرع", "Grade": "الدرجة", "Reports To": "المدير المباشر", "Holiday List": "قائمة العطل",
		"Contact Information": "معلومات الاتصال", "Phone": "الهاتف", "Personal Email": "البريد الإلكتروني الشخصي",
		"Company Email": "البريد الإلكتروني للشركة", "Preferred Contact Email": "بريد التواصل المفضل",
		"Salary Information": "معلومات الراتب", "Latest Period": "آخر فترة", "Gross Pay": "إجمالي الراتب",
		"Deductions": "الاقتطاعات", "Net Pay": "صافي الراتب", "Switching…": "جارٍ التبديل…",
		"Leave Application": "طلب إجازة", "LEAVE APPLICATION": "طلب إجازة", "HR Announcement": "إعلان الموارد البشرية",
		"HR ANNOUNCEMENT": "إعلان الموارد البشرية", "Tap to read": "اضغط للقراءة", "Archive": "أرشفة",
		"Restore": "استعادة", "Delete": "حذف", "Announcement": "إعلان", "HR Update": "تحديث الموارد البشرية",
		"No correction requested": "لم يتم طلب تصحيح", "No punches recorded": "لا توجد سجلات دخول أو خروج",
		"Mobile GPS": "نظام تحديد الموقع", "IN": "دخول", "OUT": "خروج", "hours": "ساعات",
		"hours available": "ساعات متاحة", "days available": "أيام متاحة", "Return to work": "العودة إلى العمل",
		"Location not required": "الموقع غير مطلوب", "Your attendance policy allows check-in without GPS.": "تسمح سياسة الحضور الخاصة بك بتسجيل الدخول دون استخدام الموقع الجغرافي.",
		"Log out?": "تسجيل الخروج؟", "Are you sure you want to log out of the Employee HR Portal?": "هل أنت متأكد من رغبتك في تسجيل الخروج من بوابة الموظف؟",
		"Log Out": "تسجيل الخروج", "Request failed.": "تعذر إكمال الطلب.",
		"No active leave allocations found.": "لا توجد أرصدة إجازات فعّالة.", "No leave requests found.": "لا توجد طلبات إجازة.",
		"No available leave allocation": "لا يوجد رصيد إجازة متاح", "Send Leave Request": "إرسال طلب الإجازة",
		"Sending…": "جارٍ الإرسال…", "Selecting your leave allocation and approver…": "جارٍ تحديد رصيد الإجازة والمعتمد…",
		"calendar day(s)": "أيام تقويمية", "holiday/non-working day(s) excluded": "أيام عطل أو أيام غير عاملة مستثناة",
		"No notifications in this category.": "لا توجد إشعارات في هذه الفئة.", "Delete notification?": "حذف الإشعار؟",
		"This notification will be removed permanently.": "سيتم حذف هذا الإشعار نهائياً.", "Could not update notification": "تعذر تحديث الإشعار",
		"Loading attendance…": "جارٍ تحميل الحضور…", "Loading attendance details…": "جارٍ تحميل تفاصيل الحضور…",
		"No attendance found for this filter.": "لا توجد سجلات حضور لهذا التصنيف.", "Loading leave request…": "جارٍ تحميل طلب الإجازة…",
		"Loading correction request…": "جارٍ تحميل طلب التصحيح…", "No approved leave usage found.": "لا توجد إجازات مستخدمة ومعتمدة.",
		"No information available.": "لا تتوفر معلومات.", "No submitted salary slips found.": "لا توجد قسائم راتب معتمدة.",
		"Final Approve & Submit": "الموافقة النهائية والإرسال", "Final Approve & Apply": "الموافقة النهائية والتطبيق",
		"Approve": "موافقة", "Reject": "رفض", "Final HR": "الموافقة النهائية للموارد البشرية", "Your approval": "بانتظار موافقتك",
		"HR Override": "تجاوز الموارد البشرية", "HR Override & Apply": "تجاوز الموارد البشرية والتطبيق", "HR Override Note": "ملاحظة تجاوز الموارد البشرية",
		"Location ready": "الموقع جاهز", "Location unavailable": "الموقع غير متاح", "Locating you": "جارٍ تحديد موقعك",
		"Improving accuracy": "جارٍ تحسين الدقة", "Getting your recent location…": "جارٍ الحصول على موقعك الأخير…",
		"Getting a precise GPS position…": "جارٍ تحديد موقع دقيق…", "Accuracy: {0} meters": "دقة الموقع: {0} متر",
		"GPS requires HTTPS and location support on this device.": "يتطلب تحديد الموقع اتصالاً آمناً ودعم الموقع على هذا الجهاز.",
		"Location permission was denied. Enable Location for this site in phone Settings.": "تم رفض إذن الموقع. فعّل الموقع لهذا الموقع من إعدادات الهاتف.",
		"Your location is currently unavailable.": "موقعك غير متاح حالياً.", "The GPS request timed out. Move to an open area and retry.": "انتهت مهلة تحديد الموقع. انتقل إلى مكان مفتوح وحاول مجدداً.",
		"Getting the required GPS accuracy…": "جارٍ الحصول على دقة الموقع المطلوبة…", "Checking GPS and branch geofence…": "جارٍ التحقق من الموقع ونطاق الفرع…",
		"VALIDATING…": "جارٍ التحقق…", "Correction submitted": "تم إرسال طلب التصحيح",
		"Refreshing…": "جارٍ التحديث…", "Updated": "تم التحديث", "Refresh": "تحديث",
		"Outside the allowed work location": "أنت خارج نطاق العمل المسموح",
		"You are currently about {0} from {1}.\n\nTo record attendance, move within {2} of this branch, then try again.": "أنت حالياً على بعد حوالي {0} من {1}.\n\nلتسجيل الحضور، اقترب لمسافة {2} من هذا الفرع ثم حاول مجدداً.",
		"Could not record attendance": "تعذر تسجيل الحضور", "Got it": "حسناً",
		"Your request was sent to the attendance approver.": "تم إرسال طلبك إلى معتمد الحضور.",
		"HR must create and submit a Leave Allocation for you before you can request leave.": "يجب على الموارد البشرية إنشاء واعتماد رصيد إجازة لك قبل تقديم الطلب.",
		"HR must configure a Leave Approver on your employee profile.": "يجب على الموارد البشرية تحديد معتمد الإجازة في ملفك الوظيفي.",
		"Could not load leave types": "تعذر تحميل أنواع الإجازات", "Could not update leave request": "تعذر تحديث طلب الإجازة",
		"Could not update correction": "تعذر تحديث طلب التصحيح", "No requests are waiting for your approval.": "لا توجد طلبات بانتظار موافقتك.",
		"Final HR approval": "الموافقة النهائية للموارد البشرية", "This final action will submit and apply the attendance correction. Continue?": "سيؤدي هذا الإجراء النهائي إلى اعتماد وتطبيق تصحيح الحضور. هل تريد المتابعة؟",
		"Sent to HR": "تم الإرسال إلى الموارد البشرية", "The approver step is complete. The request is still unsubmitted and is now waiting for final HR approval.": "اكتملت خطوة المعتمد. ما زال الطلب غير معتمد وهو الآن بانتظار الموافقة النهائية للموارد البشرية.",
		"Reject leave request?": "رفض طلب الإجازة؟", "This decision will end the approval process.": "سيؤدي هذا القرار إلى إنهاء مسار الموافقة.",
		"Signing in…": "جارٍ تسجيل الدخول…", "Sign In": "تسجيل الدخول", "Invalid username or password.": "اسم المستخدم أو كلمة المرور غير صحيحة.", "Invalid portal username or password.": "اسم مستخدم البوابة أو كلمة المرور غير صحيحة.",
		"Show password": "إظهار كلمة المرور", "Hide password": "إخفاء كلمة المرور", "Could not change language": "تعذر تغيير اللغة",
		"Use your browser menu and select Install app or Add to Home screen.": "استخدم قائمة المتصفح واختر تثبيت التطبيق أو الإضافة إلى الشاشة الرئيسية.",
		"{0} calendar day(s), {1} holiday/non-working day(s) excluded · {2}": "{0} يوم تقويمي، مع استثناء {1} يوم عطلة أو يوم غير عامل · {2}",
		"{0} days": "{0} أيام", "{0} hours": "{0} ساعات",
	};
	const __ = (text, replacements, context) => {
		let translated = isArabic && arabicPortalTranslations[text] ? arabicPortalTranslations[text] : nativeTranslate(text, replacements, context);
		if (isArabic && arabicPortalTranslations[text] && Array.isArray(replacements)) replacements.forEach((value, index) => { translated = translated.replaceAll(`{${index}}`, value); });
		return translated;
	};
	const portalDate = (value, options = {day: "numeric", month: "short", year: "numeric"}) => {
		const date = moment(value).toDate();
		return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat(isArabic ? "ar-LB" : "en-US", options).format(date);
	};
	const relativeTime = (value) => {
		const seconds = Math.round((moment(value).valueOf() - Date.now()) / 1000);
		const units = [["year", 31536000], ["month", 2592000], ["day", 86400], ["hour", 3600], ["minute", 60]];
		const [unit, size] = units.find(([, size]) => Math.abs(seconds) >= size) || ["second", 1];
		return new Intl.RelativeTimeFormat(isArabic ? "ar" : "en", {numeric: "auto"}).format(Math.round(seconds / size), unit);
	};
	const translateNotificationBody = (value) => {
		const text = String(value || "").replace(/<[^>]*>/g, "");
		if (!isArabic) return text;
		return text.replace(/^Your Leave Application (\S+) has been Approved by (.+)$/i, "تمت الموافقة على طلب الإجازة $1 بواسطة $2")
			.replace(/^Your Leave Application (\S+) has been Rejected by (.+)$/i, "تم رفض طلب الإجازة $1 بواسطة $2");
	};
	const savedTheme = localStorage.getItem("hr_portal_theme") || "light";
	const applyTheme = (theme, animate = false) => {
		const selected = theme === "dark" ? "dark" : "light";
		if (animate) document.documentElement.classList.add("theme-transitioning");
		document.documentElement.dataset.theme = selected;
		localStorage.setItem("hr_portal_theme", selected);
		document.querySelectorAll("[data-theme-option]").forEach((button) => button.classList.toggle("active", button.dataset.themeOption === selected));
		if (animate) setTimeout(() => document.documentElement.classList.remove("theme-transitioning"), 320);
	};
	applyTheme(savedTheme);
	if (isArabic) {
		document.documentElement.dir = "rtl";
		document.documentElement.lang = "ar";
		moment.locale?.("ar");
	}

	let coords = null;
	let busy = false;
	let status = null;
	let clockOffset = 0;
	let clockTimer = null;
	let deferredInstall = null;
	let locatingPromise = null;
	let historyLoaded = false;
	let appRefreshing = false;
	let backgroundRefreshTimer = null;
	const loadedSections = new Set();
	let deviceId = localStorage.getItem("hr_mobile_device_id");
	if (!deviceId) {
		deviceId = window.crypto && typeof window.crypto.randomUUID === "function" ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
		localStorage.setItem("hr_mobile_device_id", deviceId);
	}

	function feedback(text, kind = "") {
		const node = byId(authenticated ? "message" : "login-message");
		if (!node) return;
		node.textContent = text || "";
		node.className = `feedback ${kind}`;
	}

	function api(method, args = {}) {
		const action = method.split(".").pop();
		return new Promise((resolve, reject) => frappe.call({
			method, args, type: /^(submit|mark|archive|delete|process|set)_/.test(action) ? "POST" : "GET", silent: true,
			callback: (response) => resolve(response.message),
			error: (response) => {
				let text = __("Request failed.");
				try {
					const messages = JSON.parse(response?._server_messages || "[]");
					if (messages.length) text = JSON.parse(messages[0]).message || messages[0];
				} catch (_) { text = response?.message || text; }
				reject(new Error(text));
			},
		}));
	}

	function startClock(serverTime) {
		clockOffset = moment(serverTime).valueOf() - Date.now();
		clearInterval(clockTimer);
		const render = () => {
			const now = moment(Date.now() + clockOffset);
			setText("server-clock", now.format("HH:mm:ss"));
			setText("server-date", portalDate(now, {weekday: "long", day: "numeric", month: "long", year: "numeric"}));
		};
		render();
		clockTimer = setInterval(render, 1000);
	}

	function renderStatus(value) {
		status = value;
		startClock(value.server_time);
		const hour = moment(Date.now() + clockOffset).hour();
		const greeting = hour < 12 ? __("Good morning") : hour < 18 ? __("Good afternoon") : __("Good evening");
		setText("greeting", `${greeting}، ${value.employee_name}`);
		setText("employee", value.employee_name);
		setText("branch", value.branch || __("Not assigned"));
		setText("state", __(value.current_state));
		byId("state-dot")?.classList.toggle("in", value.current_state === "CHECKED IN");
		setText("action-label", value.next_action === "IN" ? __("CLOCK IN") : __("CLOCK OUT"));
		byId("action")?.classList.toggle("out", value.next_action === "OUT");
		setText("last-checkin", value.last_checkin ? `${value.last_checkin.log_type} · ${moment(value.last_checkin.time).format("HH:mm")}` : __("No action today"));
		document.querySelectorAll(".bottom-tabs [data-tab]").forEach((tab) => {
			const name = tab.dataset.tab;
			if (name === "approvals") return;
			tab.hidden = value.portal_tabs && !value.portal_tabs[name];
		});
		updateTabColumns();
		byId("location-info-button")?.classList.toggle("not-required", !value.require_geolocation);
		if (!value.require_geolocation) {
			setText("location-title", __("Location not required"));
			setText("location", __("Your attendance policy allows check-in without GPS."));
			byId("action").disabled = false;
		} else if (!coords) {
			locate(false);
		}
	}

	function geoPosition(options) {
		return new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject, options));
	}

	function acceptPosition(position, quiet = false) {
		coords = position.coords;
		setText("location-title", __("Location ready"));
		setText("location", __("Accuracy: {0} meters", [Math.round(coords.accuracy)]));
		if (byId("action") && !busy) byId("action").disabled = false;
		if (byId("retry")) byId("retry").hidden = true;
		if (!quiet) feedback("");
	}

	async function locate(forceAccurate = false) {
		if (locatingPromise) return locatingPromise;
		if (!window.isSecureContext || !navigator.geolocation) {
			feedback(__("GPS requires HTTPS and location support on this device."), "error");
			if (byId("retry")) byId("retry").hidden = false;
			return null;
		}
		setText("location-title", forceAccurate ? __("Improving accuracy") : __("Locating you"));
		setText("location", forceAccurate ? __("Getting a precise GPS position…") : __("Getting your recent location…"));
		locatingPromise = (async () => {
			try {
				const cacheSeconds = status?.location_cache_seconds || 120;
				const fastTimeout = (status?.fast_location_timeout || 5) * 1000;
				const preciseTimeout = (status?.high_accuracy_timeout || 12) * 1000;
				if (!forceAccurate) {
					try {
						const quick = await geoPosition({enableHighAccuracy: false, timeout: fastTimeout, maximumAge: cacheSeconds * 1000});
						acceptPosition(quick);
						geoPosition({enableHighAccuracy: true, timeout: preciseTimeout, maximumAge: 15000}).then((precise) => {
							if (!coords || precise.coords.accuracy < coords.accuracy) acceptPosition(precise, true);
						}).catch(() => {});
						return quick.coords;
					} catch (_) { /* immediately continue with precise GPS */ }
				}
				const precise = await geoPosition({enableHighAccuracy: true, timeout: preciseTimeout, maximumAge: forceAccurate ? 0 : 15000});
				acceptPosition(precise);
				return precise.coords;
			} catch (error) {
				const errors = {1: __("Location permission was denied. Enable Location for this site in phone Settings."), 2: __("Your location is currently unavailable."), 3: __("The GPS request timed out. Move to an open area and retry.")};
				setText("location-title", __("Location unavailable"));
				setText("location", errors[error.code] || error.message);
				if (byId("retry")) byId("retry").hidden = false;
				feedback(errors[error.code] || error.message, "error");
				return null;
			} finally { locatingPromise = null; }
		})();
		return locatingPromise;
	}

	async function refresh(reacquireLocation = false) {
		try {
			renderStatus(await api("hr_custom.api.attendance_clock_v2.get_status"));
			if (reacquireLocation) locate(false);
		} catch (error) { feedback(error.message, "error"); }
	}

	let attendanceRows = [];
	let attendanceFilter = "all";
	let currentAttendanceDate = null;
	function renderAttendanceHistory() {
		const container = byId("attendance-history");
		const rows = attendanceFilter === "all" ? attendanceRows : attendanceRows.filter((row) => row.category === attendanceFilter);
		container.innerHTML = rows.length ? rows.map((row) => `<div class="history-row" data-attendance-date="${frappe.utils.escape_html(String(row.attendance_date))}" data-category="${frappe.utils.escape_html(row.category || "abnormal")}"><span class="history-kind">${frappe.utils.escape_html(__(row.status || "—"))}</span><div><strong>${portalDate(row.attendance_date, {weekday: "short", day: "numeric", month: "short"})}</strong><div class="history-meta">${row.in_time ? moment(row.in_time).format("HH:mm") : "—"} – ${row.out_time ? moment(row.out_time).format("HH:mm") : "—"}</div>${row.correction_status ? `<span class="correction-status">${frappe.utils.escape_html(__(row.correction_status))}</span>` : ""}</div><strong>${Number(row.working_hours || 0).toFixed(1)}h</strong></div>`).join("") : `<div class="history-loading">${__("No attendance found for this filter.")}</div>`;
		container.querySelectorAll("[data-attendance-date]").forEach((row) => row.onclick = () => openAttendanceDetail(row.dataset.attendanceDate, row.dataset.category));
	}

	async function loadHistory() {
		historyLoaded = true;
		const container = byId("attendance-history");
		try {
			container.innerHTML = `<div class="history-loading">${__("Loading attendance…")}</div>`;
			attendanceRows = await api("hr_custom.api.portal_attendance.get_attendance_period", {from_date: byId("attendance-from").value, to_date: byId("attendance-to").value});
			renderAttendanceHistory();
		} catch (error) {
			container.innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`;
			historyLoaded = false;
		}
	}

	async function openAttendanceDetail(date, category = "abnormal") {
		currentAttendanceDate = date;
		openSheet(byId("attendance-detail-sheet"));
		setText("attendance-detail-title", portalDate(date, {day: "numeric", month: "long", year: "numeric"}));
		const container = byId("attendance-detail-content");
		container.innerHTML = `<div class="history-loading">${__("Loading attendance details…")}</div>`;
		try {
			const data = await api("hr_custom.api.attendance_detail_v2.get_attendance_detail", {attendance_date: date});
			const field = (label, value) => `<div class="leave-detail-field"><span>${label}</span><strong>${frappe.utils.escape_html(String(value || "—"))}</strong></div>`;
			const attendance = data.attendance || {};
			const schedule = data.schedule || {};
			const workPeriod = schedule.from_time && schedule.to_time ? `${String(schedule.from_time).slice(0, 5)} – ${String(schedule.to_time).slice(0, 5)}` : "—";
			const pendingReason = !attendance.name && category === "abnormal" ? (schedule.complete ? `${__("Recorded hours do not yet meet the required hours.")} (${formatNumber(Number(schedule.recorded_hours || 0).toFixed(2))}/${formatNumber(Number(schedule.working_hours || 0).toFixed(2))})` : __("A complete check-in and check-out pair is required.")) : null;
			container.innerHTML = field(__("Status"), __(attendance.status || (category === "abnormal" ? "Abnormal / Pending" : "—"))) + (pendingReason ? field(__("Why it is pending"), pendingReason) : "") + field(__("Scheduled Work Period"), workPeriod) + field(__("Required Hours"), `${formatNumber(Number(schedule.working_hours || 0).toFixed(2))} ${__("hours")}`) + field(__("Recorded Hours"), `${formatNumber(Number(attendance.working_hours || schedule.recorded_hours || 0).toFixed(2))} ${__("hours")}`) + field(__("Shift"), __(attendance.shift || schedule.shift || "—")) + `<div class="leave-detail-field"><span>${__("Punches")}</span>${data.punches.length ? data.punches.map((punch) => `<div class="approval-step"><strong><bdi>${frappe.utils.escape_html(__(punch.log_type || "—"))} · ${moment(punch.time).format("HH:mm:ss")}</bdi></strong><b>${frappe.utils.escape_html(__(punch.custom_checkin_source || punch.shift || ""))}</b></div>`).join("") : `<strong>${__("No punches recorded")}</strong>`}</div>` + `<div class="leave-detail-field"><span>${__("Correction Requests")}</span>${data.corrections.length ? data.corrections.map((row) => `<button type="button" class="correction-link" data-correction="${frappe.utils.escape_html(row.name)}">${frappe.utils.escape_html(__(row.request_type))} · ${frappe.utils.escape_html(__(row.approval_stage || row.status))}</button>`).join("") : `<strong>${__("No correction requested")}</strong>`}</div>`;
			container.querySelectorAll("[data-correction]").forEach((button) => button.onclick = () => openCorrectionDetail(button.dataset.correction));
			byId("open-correction-request").classList.toggle("is-hidden", category !== "abnormal" || data.corrections.some((row) => !["Rejected", "Applied"].includes(row.status)));
		} catch (error) { container.innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`; }
	}

	function updateCorrectionFields() {
		const type = byId("correction-type").value;
		byId("correction-in-field").classList.toggle("is-hidden", !["Missing Check In", "Wrong Check In"].includes(type));
		byId("correction-out-field").classList.toggle("is-hidden", !["Missing Check Out", "Wrong Check Out"].includes(type));
	}

	function openCorrectionForm() {
		closeSheet(byId("attendance-detail-sheet"));
		byId("correction-form").reset();
		byId("correction-date").value = currentAttendanceDate;
		byId("correction-in").value = `${currentAttendanceDate}T09:00`;
		byId("correction-out").value = `${currentAttendanceDate}T18:00`;
		updateCorrectionFields();
		openSheet(byId("correction-sheet"));
	}

	async function submitCorrection(event) {
		event.preventDefault();
		const button = byId("submit-correction");
		button.disabled = true;
		try {
			const type = byId("correction-type").value;
			await api("hr_custom.api.attendance_correction_workflow.submit_attendance_correction", {attendance_date: byId("correction-date").value, request_type: type, reason: byId("correction-reason").value, requested_check_in_time: ["Missing Check In", "Wrong Check In"].includes(type) ? byId("correction-in").value : null, requested_check_out_time: ["Missing Check Out", "Wrong Check Out"].includes(type) ? byId("correction-out").value : null});
			closeSheet(byId("correction-sheet"));
			historyLoaded = false; loadedSections.delete("approvals");
			await loadHistory();
			await showAppDialog({title: __("Correction submitted"), message: __("Your request was sent to the attendance approver."), icon: "✓"});
		} catch (error) { setText("correction-message", error.message); }
		finally { button.disabled = false; }
	}

	function formatNumber(value) { return Number(value || 0).toLocaleString(isArabic ? "ar-LB" : undefined, {maximumFractionDigits: 2}); }

	async function loadLeaves(force = false) {
		if (!force && loadedSections.has("leaves")) return;
		const balances = byId("leave-balances"), requests = byId("leave-requests");
		try {
			const data = await api("hr_custom.api.mobile_attendance.get_leave_portal_data");
			balances.innerHTML = data.balances.length ? data.balances.map((row) => `<div class="balance-row"><div class="balance-title"><strong>${frappe.utils.escape_html(__(row.leave_type))}</strong><strong>${formatNumber(row.remaining)} ${__("remaining")}</strong></div><div class="balance-numbers"><div class="used-leave-link" data-leave-type="${frappe.utils.escape_html(row.leave_type)}"><span>${__("Used")}</span><strong>${formatNumber(row.used)}</strong></div><div><span>${__("Allocated")}</span><strong>${formatNumber(row.allocated)}</strong></div></div></div>`).join("") : `<div class="history-loading">${__("No active leave allocations found.")}</div>`;
			requests.innerHTML = data.requests.length ? data.requests.map((row) => `<div class="leave-row" data-leave="${frappe.utils.escape_html(row.name)}"><div class="row-between"><strong>${frappe.utils.escape_html(__(row.leave_type))}</strong><span class="status-pill">${frappe.utils.escape_html(__(row.status))}</span></div><span class="row-subtle">${portalDate(row.from_date)} – ${portalDate(row.to_date)} · ${formatNumber(row.total_leave_days)} ${__("days")}</span></div>`).join("") : `<div class="history-loading">${__("No leave requests found.")}</div>`;
			requests.querySelectorAll("[data-leave]").forEach((row) => row.onclick = () => openLeaveDetail(row.dataset.leave));
			balances.querySelectorAll(".used-leave-link").forEach((used) => used.onclick = () => {
				const matching = data.requests.filter((row) => row.leave_type === used.dataset.leaveType && row.status === "Approved");
				if (matching.length === 1) openLeaveDetail(matching[0].name);
				else {
					requests.innerHTML = matching.length ? matching.map((row) => `<div class="leave-row" data-leave="${frappe.utils.escape_html(row.name)}"><div class="row-between"><strong>${frappe.utils.escape_html(__(row.leave_type))}</strong><span class="status-pill">${frappe.utils.escape_html(__(row.status))}</span></div><span class="row-subtle"><bdi>${portalDate(row.from_date)} – ${portalDate(row.to_date)}</bdi></span></div>`).join("") : `<div class="history-loading">${__("No approved leave usage found.")}</div>`;
					requests.querySelectorAll("[data-leave]").forEach((row) => row.onclick = () => openLeaveDetail(row.dataset.leave));
					byId("leave-requests").closest("details").open = true;
				}
			});
			loadedSections.add("leaves");
		} catch (error) { balances.innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`; }
	}

	let currentLeaveDetail = null;
	let currentCorrectionDetail = null;
	let currentCorrectionContext = null;
	async function openLeaveDetail(name, allowAction = false) {
		currentLeaveDetail = name;
		openSheet(byId("leave-detail-sheet"));
		const container = byId("leave-detail-content");
		container.innerHTML = `<div class="history-loading">${__("Loading leave request…")}</div>`;
		try {
			const [row, context] = await Promise.all([
				api("hr_custom.api.mobile_attendance.get_portal_leave_detail", {name}),
				api("hr_custom.services.simple_leave.get_leave_approval_context", {name}),
			]);
			setText("leave-detail-title", __(row.leave_type || "Leave Request"));
			const field = (label, value) => `<div class="leave-detail-field"><span>${label}</span><strong>${frappe.utils.escape_html(String(value || "—"))}</strong></div>`;
			container.innerHTML = field(__("Employee"), row.employee_name || row.employee) + field(__("Dates"), `${portalDate(row.from_date)} – ${portalDate(row.to_date)}`) + field(__("Amount"), `${formatNumber(row.total_leave_days)} ${__("days")}`) + field(__("Status"), __(row.stage || row.status)) + field(__("Reason"), row.description) + `<div class="leave-detail-field"><span>${__("Approval Progress")}</span>${(row.steps || []).map((step) => `<div class="approval-step"><strong>${frappe.utils.escape_html(step.approver_name || step.approver)}</strong><b>${frappe.utils.escape_html(__(step.status))}</b></div>`).join("") || `<strong>${__("No approval steps")}</strong>`}</div>`;
			byId("leave-detail-actions").classList.toggle("is-hidden", !(allowAction && context.can_act));
			setText("approve-leave", context.is_final_hr_step ? __("Final Approve & Submit") : __("Approve"));
		} catch (error) { container.innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`; }
	}

	async function openCorrectionDetail(name, allowAction = false) {
		currentCorrectionDetail = name;
		currentCorrectionContext = null;
		openSheet(byId("correction-detail-sheet"));
		const container = byId("correction-detail-content");
		container.innerHTML = `<div class="history-loading">${__("Loading correction request…")}</div>`;
		try {
			const row = await api("hr_custom.api.attendance_correction_workflow.get_correction_detail", {name});
			currentCorrectionContext = row.context || {};
			setText("correction-detail-title", row.request_type || __("Attendance Correction"));
			const field = (label, value) => `<div class="leave-detail-field"><span>${label}</span><strong>${frappe.utils.escape_html(String(value || "—"))}</strong></div>`;
			container.innerHTML = field(__("Employee"), row.employee_name || row.employee) + field(__("Date"), moment(row.attendance_date).format("D MMMM YYYY")) + field(__("Status"), row.stage || row.status) + field(__("Requested Check In"), row.requested_check_in_time ? moment(row.requested_check_in_time).format("D MMM YYYY HH:mm") : "—") + field(__("Requested Check Out"), row.requested_check_out_time ? moment(row.requested_check_out_time).format("D MMM YYYY HH:mm") : "—") + field(__("Reason"), row.reason) + (row.hr_override_note ? field(__("HR Override Note"), row.hr_override_note) : "") + `<div class="leave-detail-field"><span>${__("Approval Progress")}</span>${(row.steps || []).map((step) => `<div class="approval-step"><strong>${frappe.utils.escape_html(step.approver_name || step.approver)}</strong><b>${frappe.utils.escape_html(step.status)}</b></div>`).join("") || `<strong>${__("Waiting for HR")}</strong>`}</div>`;
			const canAct = allowAction && row.context?.can_act;
			byId("correction-detail-actions").classList.toggle("is-hidden", !canAct);
			byId("correction-override-help").classList.toggle("is-hidden", !row.context?.is_hr_override);
			setText("approve-correction", row.context?.is_final_hr_step ? __("Final Approve & Apply") : row.context?.is_hr_override ? __("HR Override & Apply") : __("Approve"));
		} catch (error) { container.innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`; }
	}

	async function actOnCorrection(action) {
		if (!currentCorrectionDetail) return;
		if (action === "approve" && currentCorrectionContext?.is_final_hr_step) {
			const confirmed = await showAppDialog({title: __("Final HR approval"), message: __("This final action will submit and apply the attendance correction. Continue?"), icon: "✓", confirmLabel: __("Final Approve & Apply"), showCancel: true});
			if (!confirmed) return;
		}
		try {
			byId("approve-correction").disabled = true; byId("reject-correction").disabled = true;
			const result = await api("hr_custom.api.attendance_correction_workflow.process_correction_approval", {name: currentCorrectionDetail, action, remarks: byId("correction-approval-note").value});
			closeSheet(byId("correction-detail-sheet"));
			loadedSections.delete("approvals"); historyLoaded = false;
			await loadApprovals(true);
			if (action === "approve" && result?.approval_stage === "Pending HR Approval") await showAppDialog({title: __("Sent to HR"), message: __("The approver step is complete. The request is still unsubmitted and is now waiting for final HR approval."), icon: "→"});
		} catch (error) { await showAppDialog({title: __("Could not update correction"), message: error.message, icon: "!"}); }
		finally { byId("approve-correction").disabled = false; byId("reject-correction").disabled = false; }
	}

	function setTabBadge(name, count) {
		const badge = document.querySelector(`[data-tab-badge="${name}"]`);
		if (!badge) return;
		const value = Math.max(0, Number(count || 0));
		badge.textContent = value > 99 ? "99+" : String(value);
		badge.hidden = value === 0;
	}

	function updateNotificationTabBadges(items) {
		const unread = (items || []).filter((row) => !Number(row.read) && !Number(row.custom_archived));
		setTabBadge("leaves", unread.filter((row) => row.reference_document_type === "Leave Application" && Number(row.is_own_record)).length);
		setTabBadge("salary", unread.filter((row) => row.reference_document_type === "Salary Slip").length);
	}

	async function loadApprovals(force = false) {
		if (!force && loadedSections.has("approvals")) return;
		const container = byId("approval-list");
		try {
			const [data, corrections] = await Promise.all([api("hr_custom.api.mobile_attendance.get_leave_approval_queue"), api("hr_custom.api.attendance_correction_workflow.get_correction_approval_queue")]);
			const tab = document.querySelector('[data-tab="approvals"]');
			tab.hidden = !(data.can_review || corrections.can_review); updateTabColumns();
			setTabBadge("approvals", data.items.length + corrections.items.length);
			const leaveHtml = data.items.map((row) => `<div class="approval-row" data-leave="${frappe.utils.escape_html(row.name)}"><div class="row-between"><strong>${frappe.utils.escape_html(row.employee_name || row.employee)}</strong><span class="status-pill">${row.review_mode === "hr" ? __("Final HR") : __("Your approval")}</span></div><strong>${frappe.utils.escape_html(row.leave_type)}</strong><span class="row-subtle">${moment(row.from_date).format("D MMM YYYY")} – ${moment(row.to_date).format("D MMM YYYY")} · ${formatNumber(row.total_leave_days)} ${__("days")}</span></div>`).join("");
			const correctionHtml = corrections.items.map((row) => `<div class="approval-row" data-correction="${frappe.utils.escape_html(row.name)}"><div class="row-between"><strong>${frappe.utils.escape_html(row.employee_name || row.employee)}</strong><span class="status-pill">${row.review_mode === "hr_override" ? __("HR Override") : row.review_mode === "hr" ? __("Final HR") : __("Your approval")}</span></div><strong>${frappe.utils.escape_html(row.request_type)}</strong><span class="row-subtle">${moment(row.attendance_date).format("D MMM YYYY")} · ${__("Attendance correction")}</span></div>`).join("");
			container.innerHTML = leaveHtml + correctionHtml || `<div class="history-loading">${__("No requests are waiting for your approval.")}</div>`;
			container.querySelectorAll("[data-leave]").forEach((row) => row.onclick = () => openLeaveDetail(row.dataset.leave, true));
			container.querySelectorAll("[data-correction]").forEach((row) => row.onclick = () => openCorrectionDetail(row.dataset.correction, true));
			loadedSections.add("approvals");
		} catch (error) { container.innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`; }
	}

	function updateTabColumns() {
		const visible = [...document.querySelectorAll(".bottom-tabs [data-tab]")].filter((tab) => !tab.hidden).length;
		document.querySelector(".bottom-tabs").style.setProperty("--portal-tab-count", visible || 4);
	}

	async function loadSalary() {
		if (loadedSections.has("salary")) return;
		const container = byId("salary-list");
		try {
			const rows = await api("hr_custom.api.mobile_attendance.get_salary_portal_data");
			container.innerHTML = rows.length ? rows.map((row) => `<div class="salary-row"><div class="row-between"><strong>${moment(row.end_date).format("MMMM YYYY")}</strong><strong>${frappe.utils.escape_html(row.currency || "")} ${formatNumber(row.net_pay)}</strong></div><span class="row-subtle">${__("Gross")}: ${formatNumber(row.gross_pay)} · ${__("Deductions")}: ${formatNumber(row.total_deduction)}</span></div>`).join("") : `<div class="history-loading">${__("No submitted salary slips found.")}</div>`;
			loadedSections.add("salary");
		} catch (error) { container.innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`; }
	}

	async function loadProfile() {
		if (loadedSections.has("profile")) return;
		document.querySelectorAll("[data-language]").forEach((button) => button.classList.toggle("active", button.dataset.language === (isArabic ? "ar" : "en")));
		applyTheme(localStorage.getItem("hr_portal_theme") || "light");
		try {
			const row = await api("hr_custom.api.mobile_attendance.get_profile_data");
			setText("profile-name", row.employee_name); setText("profile-id", row.name); setText("profile-avatar", (row.employee_name || "?").trim().charAt(0).toUpperCase());
			const salary = row.salary?.[0];
			const groups = [
				[__("Employee Details"), {employee_name: __("Employee Name"), gender: __("Gender"), date_of_birth: __("Date of Birth"), date_of_joining: __("Date of Joining"), employment_type: __("Employment Type")}],
				[__("Company Information"), {company: __("Company"), department: __("Department"), designation: __("Designation"), branch: __("Branch"), grade: __("Grade"), reports_to: __("Reports To"), holiday_list: __("Holiday List")}],
				[__("Contact Information"), {cell_number: __("Phone"), personal_email: __("Personal Email"), company_email: __("Company Email"), prefered_contact_email: __("Preferred Contact Email")}],
			];
			const detailRows = (values, labels) => Object.entries(labels).filter(([key]) => values[key]).map(([key, label]) => `<div class="profile-detail"><span>${label}</span><strong>${frappe.utils.escape_html(__(String(values[key])))}</strong></div>`).join("") || `<div class="history-loading">${__("No information available.")}</div>`;
			let html = groups.map(([title, labels], index) => `<details class="profile-section" ${index === 0 ? "open" : ""}><summary><span>${title}</span><b>⌄</b></summary><div>${detailRows(row, labels)}</div></details>`).join("");
			const salaryValues = salary ? {period: moment(salary.end_date).format("MMMM YYYY"), gross: `${salary.currency || ""} ${formatNumber(salary.gross_pay)}`, deductions: `${salary.currency || ""} ${formatNumber(salary.total_deduction)}`, net: `${salary.currency || ""} ${formatNumber(salary.net_pay)}`} : {};
			html += `<details class="profile-section"><summary><span>${__("Salary Information")}</span><b>⌄</b></summary><div>${detailRows(salaryValues, {period: __("Latest Period"), gross: __("Gross Pay"), deductions: __("Deductions"), net: __("Net Pay")})}</div></details>`;
			byId("profile-details").innerHTML = html;
			loadedSections.add("profile");
		} catch (error) { byId("profile-details").innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`; }
	}

	const tabOrder = ["attendance", "leaves", "approvals", "salary", "profile"];
	let activeSection = "attendance";
	function showSection(name, direction = null) {
		if (name === activeSection) return;
		const previousIndex = tabOrder.indexOf(activeSection), nextIndex = tabOrder.indexOf(name);
		const animation = direction || (nextIndex > previousIndex ? "next" : "prev");
		document.querySelectorAll(".portal-view").forEach((view) => view.classList.toggle("is-hidden", view.id !== `${name}-view`));
		const view = byId(`${name}-view`);
		view?.classList.remove("tab-enter-next", "tab-enter-prev");
		requestAnimationFrame(() => view?.classList.add(`tab-enter-${animation}`));
		document.querySelectorAll(".bottom-tabs [data-tab]").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
		if (byId("location-info-button")) byId("location-info-button").hidden = name !== "attendance";
		if (name === "leaves") loadLeaves(); else if (name === "approvals") loadApprovals(); else if (name === "salary") loadSalary(); else if (name === "profile") loadProfile();
		activeSection = name;
		window.scrollTo({top: 0, behavior: "smooth"});
	}

	function overlayIsOpen() {
		return Boolean(document.querySelector(".app-dialog:not(.is-hidden),.notification-sheet:not(.is-hidden),.leave-sheet:not(.is-hidden),.install-sheet:not(.is-hidden)"));
	}

	async function refreshApp({background = false, reacquireLocation = false} = {}) {
		if (appRefreshing || !authenticated) return;
		appRefreshing = true;
		const button = byId("refresh-button");
		button.disabled = true;
		button.classList.add("refreshing");
		try {
			const tasks = [refresh(reacquireLocation), loadNotifications(), loadApprovals(true)];
			if (byId("history-card")?.open) tasks.push(loadHistory());
			if (activeSection === "leaves") tasks.push(loadLeaves(true));
			if (activeSection === "salary") { loadedSections.delete("salary"); tasks.push(loadSalary()); }
			if (activeSection === "profile") { loadedSections.delete("profile"); tasks.push(loadProfile()); }
			await Promise.allSettled(tasks);
		} finally {
			appRefreshing = false;
			button.disabled = false;
			button.classList.remove("refreshing");
		}
	}

	function openSheet(sheet) {
		sheet.classList.remove("is-hidden", "is-closing");
		document.body.style.overflow = "hidden";
	}
	function closeSheet(sheet) {
		if (!sheet || sheet.classList.contains("is-hidden")) return;
		sheet.classList.add("is-closing");
		setTimeout(() => { sheet.classList.add("is-hidden"); sheet.classList.remove("is-closing"); document.body.style.overflow = ""; }, 220);
	}

	function showAppDialog({title, message, icon = "i", confirmLabel = __("OK"), showCancel = false, danger = false, tone = ""}) {
		return new Promise((resolve) => {
			const dialog = byId("app-dialog"), confirm = byId("app-dialog-confirm"), cancel = byId("app-dialog-cancel");
			setText("app-dialog-title", title); setText("app-dialog-message", message); setText("app-dialog-icon", icon); setText("app-dialog-confirm", confirmLabel);
			cancel.hidden = !showCancel; confirm.classList.toggle("danger", danger); dialog.classList.toggle("warning", tone === "warning");
			dialog.classList.remove("is-hidden", "is-closing"); document.body.style.overflow = "hidden";
			const finish = (answer) => {
				dialog.classList.add("is-closing");
				setTimeout(() => { dialog.classList.add("is-hidden"); dialog.classList.remove("is-closing"); document.body.style.overflow = ""; resolve(answer); }, 180);
			};
			confirm.onclick = () => finish(true); cancel.onclick = () => finish(false);
			dialog.onclick = (event) => { if (event.target === dialog && showCancel) finish(false); };
		});
	}

	function autoCommitDatePicker(input) {
		if (!input) return;
		input.addEventListener("input", () => {
			if (!/^\d{4}-\d{2}-\d{2}$/.test(input.value)) return;
			// iOS keeps its native date wheel open until Done is tapped. Commit the
			// selected value immediately and dismiss the wheel for a one-tap flow.
			input.dispatchEvent(new Event("change", {bubbles: true}));
			setTimeout(() => input.blur(), 0);
		});
	}

	async function loadNotifications() {
		const list = byId("notification-list");
		try {
			const data = await api("hr_custom.api.mobile_attendance.get_portal_notifications", {limit: 100, include_archived: 1});
			const badge = byId("notification-badge");
			badge.textContent = data.unread || 0; badge.hidden = !data.unread;
			data.items = (data.items || []).map((row) => {
				if (row.reference_document_type !== "HR Announcement") return row;
				const raw = String(row.body || row.message || "").replace(/<[^>]*>/g, "").trim();
				const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
				let fallbackTitle = lines[0] || __("Announcement");
				let fallbackBody = lines.slice(1).join("\n");
				if (lines.length < 2 && raw.includes(":")) {
					const separator = raw.indexOf(":");
					fallbackTitle = raw.slice(0, separator).trim() || fallbackTitle;
					fallbackBody = raw.slice(separator + 1).trim();
				}
				return {...row, category: Number(row.custom_archived) ? "archived" : "announcements", title: row.title && row.title !== "HR Announcement" ? row.title : fallbackTitle, body: row.body || fallbackBody};
			});
			updateNotificationTabBadges(data.items);
			list.innerHTML = data.items.map((row) => `<div class="notification-row ${row.read ? "" : "unread"}" data-category="${frappe.utils.escape_html(row.category || "updates")}" data-archived="${Number(row.custom_archived) ? 1 : 0}" data-notification="${frappe.utils.escape_html(row.name)}" data-reference-type="${frappe.utils.escape_html(row.reference_document_type || "")}" data-reference-name="${frappe.utils.escape_html(row.reference_document_name || "")}" aria-expanded="false" role="button" tabindex="0"><span class="notification-kind">${row.reference_document_type === "Salary Slip" ? "▤" : row.reference_document_type === "HR Announcement" ? "!" : "✓"}</span><span class="notification-content"><span class="notification-type">${frappe.utils.escape_html(__(row.reference_document_type || "HR Update"))}</span><strong class="notification-title">${frappe.utils.escape_html(__(row.title || row.reference_document_type || "HR Update"))}</strong><span class="notification-preview">${frappe.utils.escape_html(translateNotificationBody(row.body || row.message))}</span><small>${relativeTime(row.creation)} · ${__("Tap to read")}</small><span class="notification-actions"><button type="button" data-notification-action="${Number(row.custom_archived) ? "unarchive" : "archive"}">${Number(row.custom_archived) ? __("Restore") : __("Archive")}</button><button type="button" class="danger" data-notification-action="delete">${__("Delete")}</button></span></span></div>`).join("") + `<div class="notification-empty">${__("No notifications in this category.")}</div>`;
			list.querySelectorAll(".notification-row").forEach((row) => row.addEventListener("click", async (event) => {
				if (event.target.closest("[data-notification-action]")) return;
				const expanded = row.getAttribute("aria-expanded") === "true";
				row.setAttribute("aria-expanded", String(!expanded));
				if (!expanded && row.classList.contains("unread")) {
					try {
						await api("hr_custom.api.mobile_attendance.mark_portal_notification_read", {notification: row.dataset.notification});
						row.classList.remove("unread");
						const remaining = Math.max(0, Number(badge.textContent || 0) - 1);
						badge.textContent = remaining; badge.hidden = remaining === 0;
						const tabName = row.dataset.referenceType === "Leave Application" ? "leaves" : row.dataset.referenceType === "Salary Slip" ? "salary" : null;
						if (tabName) {
							const tabBadge = document.querySelector(`[data-tab-badge="${tabName}"]`);
							setTabBadge(tabName, Math.max(0, Number(tabBadge?.textContent || 0) - 1));
						}
					} catch (_) { /* keep it unread when the server rejects the update */ }
				}
				if (row.dataset.referenceType === "Leave Application" && row.dataset.referenceName) { closeNotifications(); setTimeout(() => openLeaveDetail(row.dataset.referenceName, true), 230); }
				if (row.dataset.referenceType === "Attendance Correction Request" && row.dataset.referenceName) { closeNotifications(); setTimeout(() => openCorrectionDetail(row.dataset.referenceName, true), 230); }
			}));
			list.querySelectorAll("[data-notification-action]").forEach((button) => button.addEventListener("click", async (event) => {
				event.stopPropagation();
				await manageNotification(button.closest(".notification-row"), button.dataset.notificationAction, button);
			}));
			applyNotificationFilter(document.querySelector("[data-notification-filter].active")?.dataset.notificationFilter || "all");
			byId("enable-notifications").hidden = !data.push_enabled;
		} catch (error) { list.innerHTML = `<div class="history-loading">${frappe.utils.escape_html(error.message)}</div>`; }
	}

	function applyNotificationFilter(category) {
		document.querySelectorAll("[data-notification-filter]").forEach((button) => button.classList.toggle("active", button.dataset.notificationFilter === category));
		let visible = 0;
		document.querySelectorAll("#notification-list .notification-row").forEach((row) => {
			row.hidden = category === "all" ? row.dataset.archived === "1" : row.dataset.category !== category;
			if (!row.hidden) visible += 1;
		});
		const empty = document.querySelector("#notification-list .notification-empty");
		if (empty) empty.hidden = visible > 0;
	}

	async function manageNotification(row, action, button = null) {
		if (!row) return;
		if (action === "delete") {
			const confirmed = await showAppDialog({title: __("Delete notification?"), message: __("This notification will be removed permanently."), icon: "!", confirmLabel: __("Delete"), showCancel: true, danger: true});
			if (!confirmed) return;
		}
		if (button) button.disabled = true;
		try {
			await api(`hr_custom.api.mobile_attendance.${action}_portal_notification`, {notification: row.dataset.notification});
			await loadNotifications();
		} catch (error) { await showAppDialog({title: __("Could not update notification"), message: error.message, icon: "!"}); }
	}


	async function openNotifications() {
		openSheet(byId("notification-sheet"));
		await loadNotifications();
	}
	function closeNotifications() { closeSheet(byId("notification-sheet")); }

	async function openLeaveRequest() {
		const today = moment().format("YYYY-MM-DD");
		if (!byId("leave-from-date").value) byId("leave-from-date").value = today;
		if (!byId("leave-to-date").value) byId("leave-to-date").value = byId("leave-from-date").value;
		openSheet(byId("leave-sheet"));
		await loadAvailableLeaveTypes();
		scheduleLeavePreview();
	}

	function closeLeaveRequest() {
		closeSheet(byId("leave-sheet"));
	}

	function enablePullDownDismiss(sheet) {
		const card = sheet?.querySelector(".leave-sheet-card");
		if (!sheet || !card) return;
		let startY = null;
		card.addEventListener("touchstart", (event) => {
			startY = event.touches.length === 1 && card.scrollTop <= 0 ? event.touches[0].clientY : null;
		}, {passive: true});
		card.addEventListener("touchend", (event) => {
			if (startY !== null && event.changedTouches[0].clientY - startY > 75) closeSheet(sheet);
			startY = null;
		}, {passive: true});
	}

	let leavePreviewTimer = null;
	async function loadAvailableLeaveTypes() {
		const select = byId("leave-type"), previous = select.value;
		const requirements = byId("leave-requirements");
		try {
			const data = await api("hr_custom.services.simple_leave.get_available_leave_types", {from_date: byId("leave-from-date").value, to_date: byId("leave-to-date").value});
			select.innerHTML = data.leave_types.length ? data.leave_types.map((row) => `<option value="${frappe.utils.escape_html(row.leave_type)}" data-unit="${row.leave_unit}">${frappe.utils.escape_html(__(row.leave_type))} · ${formatNumber(row.balance)} ${__(row.leave_unit === "Hours" ? "hours available" : "days available")}</option>`).join("") : `<option value="">${__("No available leave allocation")}</option>`;
			if (previous && data.leave_types.some((row) => row.leave_type === previous)) select.value = previous;
			requirements.classList.toggle("is-hidden", data.has_approver && data.leave_types.length);
			requirements.textContent = !data.leave_types.length ? __("HR must create and submit a Leave Allocation for you before you can request leave.") : !data.has_approver ? __("HR must configure a Leave Approver on your employee profile.") : "";
			updateSelectedLeaveType();
		} catch (error) {
			select.innerHTML = `<option value="">${__("Could not load leave types")}</option>`;
			requirements.classList.remove("is-hidden"); requirements.textContent = error.message;
		}
	}
	function updateSelectedLeaveType() {
		const option = byId("leave-type").selectedOptions[0];
		byId("leave-unit").value = option?.dataset.unit || "Days";
		updateHourlyFields();
	}
	async function previewLeave() {
		const fromDate = byId("leave-from-date").value;
		const toDate = byId("leave-to-date").value;
		if (!fromDate || !toDate || toDate < fromDate) return;
		try {
			if (!byId("leave-type").value) return;
			const result = await api("hr_custom.services.simple_leave.preview_simple_leave", {from_date: fromDate, to_date: toDate, leave_type: byId("leave-type").value, leave_duration: byId("leave-duration").value, partial_hours: byId("leave-partial-hours").value});
			byId("leave-preview").classList.remove("is-hidden");
			setText("leave-preview-amount", result.leave_unit === "Hours" ? __("{0} hours", [result.total_leave_hours]) : __("{0} days", [result.leave_days]));
			setText("leave-preview-return", portalDate(result.return_to_work_date, {day: "numeric", month: "long", year: "numeric"}));
			setText("leave-preview-note", __("{0} calendar day(s), {1} holiday/non-working day(s) excluded · {2}", [formatNumber(result.calendar_days), formatNumber(result.excluded_days), __(result.leave_type)]));
			byId("leave-message").textContent = "";
		} catch (error) {
			byId("leave-preview").classList.add("is-hidden");
			const message = byId("leave-message"); message.className = "feedback error"; message.textContent = error.message;
		}
	}
	function scheduleLeavePreview() { clearTimeout(leavePreviewTimer); leavePreviewTimer = setTimeout(previewLeave, 250); }
	function updateHourlyFields() {
		const hourly = byId("leave-unit").value === "Hours";
		byId("hourly-leave-fields").classList.toggle("is-hidden", !hourly);
		byId("partial-hours-field").classList.toggle("is-hidden", !hourly || byId("leave-duration").value !== "Partial Hours");
		if (hourly && byId("leave-duration").value === "Partial Hours") byId("leave-to-date").value = byId("leave-from-date").value;
		scheduleLeavePreview();
	}

	async function submitSimpleLeave(event) {
		event.preventDefault();
		const button = byId("submit-leave-request");
		const message = byId("leave-message");
		button.disabled = true;
		button.textContent = __("Sending…");
		message.className = "feedback";
		message.textContent = __("Selecting your leave allocation and approver…");
		try {
			const result = await api("hr_custom.services.simple_leave.submit_simple_leave", {from_date: byId("leave-from-date").value, to_date: byId("leave-to-date").value, reason: byId("leave-reason").value, leave_type: byId("leave-type").value, leave_duration: byId("leave-duration").value, partial_hours: byId("leave-partial-hours").value});
			message.className = "feedback success";
			const amount = result.leave_unit === "Hours" ? __("{0} hours", [result.leave_hours]) : __("{0} days", [result.leave_days]);
			message.textContent = __("Leave request {0} for {1} sent to {2} approver(s). Return to work: {3}.", [result.name, amount, formatNumber(result.approver_count), portalDate(result.return_to_work_date, {day: "numeric", month: "long", year: "numeric"})]);
			byId("simple-leave-form").reset();
			loadedSections.delete("leaves");
			setTimeout(closeLeaveRequest, 1600);
		} catch (error) {
			message.className = "feedback error";
			message.textContent = error.message;
		} finally {
			button.disabled = false;
			button.textContent = __("Send Leave Request");
		}
	}

	byId("password-toggle")?.addEventListener("click", (event) => {
			event.preventDefault();
			const input = byId("login-password");
			const showing = input.type === "text";
			input.type = showing ? "password" : "text";
			byId("password-toggle").setAttribute("aria-label", showing ? __("Show password") : __("Hide password"));
	});
	if (!authenticated) {
		byId("login-form")?.addEventListener("submit", async (event) => {
			event.preventDefault();
			const button = byId("login-button");
			button.disabled = true; setText("login-button", __("Signing in…")); feedback("");
			try {
				const body = new URLSearchParams({username: byId("login-username").value.trim(), password: byId("login-password").value});
				const response = await fetch("/api/method/hr_custom.api.portal_auth.login", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", Accept: "application/json"}, body});
				const data = await response.json();
				if (!response.ok || !data.message?.authenticated) throw new Error(data.message || __("Invalid portal username or password."));
				localStorage.setItem("hr_attendance_logged_in", "1"); location.replace(`/attendance?login=${Date.now()}`);
			} catch (error) { button.disabled = false; setText("login-button", __("Sign In")); feedback(error.message || __("Invalid portal username or password."), "error"); }
		});
		return;
	}

	localStorage.setItem("hr_attendance_logged_in", "1");
	byId("retry").onclick = () => locate(true);
	byId("refresh-button").onclick = () => refreshApp();
	byId("notification-button").onclick = openNotifications;
	byId("notification-close").onclick = closeNotifications;
	byId("notification-sheet").addEventListener("click", (event) => { if (event.target === byId("notification-sheet")) closeNotifications(); });
	byId("leave-detail-close").onclick = () => closeSheet(byId("leave-detail-sheet"));
	byId("leave-detail-sheet").addEventListener("click", (event) => { if (event.target === byId("leave-detail-sheet")) closeSheet(byId("leave-detail-sheet")); });
	byId("attendance-detail-close").onclick = () => closeSheet(byId("attendance-detail-sheet"));
	byId("correction-close").onclick = () => closeSheet(byId("correction-sheet"));
	byId("correction-detail-close").onclick = () => closeSheet(byId("correction-detail-sheet"));
	["attendance-detail-sheet", "correction-sheet", "correction-detail-sheet"].forEach((id) => {
		byId(id).addEventListener("click", (event) => { if (event.target === byId(id)) closeSheet(byId(id)); });
		enablePullDownDismiss(byId(id));
	});
	byId("open-correction-request").onclick = openCorrectionForm;
	byId("correction-type").onchange = updateCorrectionFields;
	byId("correction-form").onsubmit = submitCorrection;
	byId("approve-correction").onclick = () => actOnCorrection("approve");
	byId("reject-correction").onclick = () => actOnCorrection("reject");
	enablePullDownDismiss(byId("leave-sheet"));
	enablePullDownDismiss(byId("leave-detail-sheet"));
	document.querySelectorAll("[data-theme-option]").forEach((button) => button.addEventListener("click", () => {
		if (button.classList.contains("active")) return;
		applyTheme(button.dataset.themeOption, true);
	}));
	document.querySelectorAll("[data-language]").forEach((button) => button.addEventListener("click", async () => {
		if (button.classList.contains("active")) return;
		const languageButtons = [...document.querySelectorAll("[data-language]")];
		const setting = byId("language-setting");
		const statusText = byId("language-status");
		const originalStatus = statusText?.textContent || "";
		languageButtons.forEach((item) => { item.disabled = true; });
		button.classList.add("is-loading");
		setting?.classList.add("is-switching");
		if (statusText) statusText.textContent = button.dataset.language === "ar" ? "جارٍ التبديل…" : __("Switching…");
		await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
		try {
			try {
				await api("hr_custom.api.mobile_attendance.set_portal_language", {language: button.dataset.language});
			} catch (routeError) {
				// Keep the switch usable while long-running Frappe workers still have
				// the previous module loaded. This standard endpoint is already live.
				await api("frappe.client.set_value", {
					doctype: "User",
					name: frappe.session.user,
					fieldname: "language",
					value: button.dataset.language,
				});
			}
			location.replace(`/attendance?lang=${button.dataset.language}&changed=${Date.now()}`);
		} catch (error) {
			languageButtons.forEach((item) => { item.disabled = false; });
			button.classList.remove("is-loading");
			setting?.classList.remove("is-switching");
			if (statusText) statusText.textContent = originalStatus;
			await showAppDialog({title: __("Could not change language"), message: error.message, icon: "!"});
		}
	}));
	async function actOnPortalLeave(action) {
		if (!currentLeaveDetail) return;
		if (action === "reject") {
			const confirmed = await showAppDialog({title: __("Reject leave request?"), message: __("This decision will end the approval process."), icon: "!", confirmLabel: __("Reject"), showCancel: true, danger: true});
			if (!confirmed) return;
		}
		try {
			await api("hr_custom.services.simple_leave.process_leave_approval", {name: currentLeaveDetail, action, remarks: byId("leave-approval-remarks").value});
			closeSheet(byId("leave-detail-sheet"));
			loadedSections.delete("approvals"); loadedSections.delete("leaves");
			await loadApprovals(true);
			if (activeSection === "leaves") await loadLeaves(true);
		} catch (error) { await showAppDialog({title: __("Could not update leave request"), message: error.message, icon: "!"}); }
	}
	byId("approve-leave").onclick = () => actOnPortalLeave("approve");
	byId("reject-leave").onclick = () => actOnPortalLeave("reject");
	let notificationPullStart = null;
	byId("notification-sheet").addEventListener("touchstart", (event) => {
		const list = byId("notification-list");
		if (event.touches.length === 1 && list.scrollHeight <= list.clientHeight + 2) notificationPullStart = event.touches[0].clientY;
	}, {passive: true});
	byId("notification-sheet").addEventListener("touchend", (event) => {
		if (notificationPullStart !== null && event.changedTouches[0].clientY - notificationPullStart > 70) closeNotifications();
		notificationPullStart = null;
	}, {passive: true});
	document.querySelectorAll("[data-notification-filter]").forEach((button) => button.addEventListener("click", () => applyNotificationFilter(button.dataset.notificationFilter)));
	byId("location-info-button").onclick = async () => {
		if (!status?.require_geolocation) {
			await showAppDialog({title: __("Location not required"), message: __("Your attendance policy allows check-in without GPS."), icon: "⌖"});
			return;
		}
		if (!coords) await locate(true);
		await showAppDialog({title: byId("location-title").textContent, message: byId("location").textContent, icon: coords ? "✓" : "!"});
	};
	byId("history-card").addEventListener("toggle", (event) => { if (event.target.open) loadHistory(); });
	byId("filter-attendance").addEventListener("click", loadHistory);
	document.querySelectorAll("[data-attendance-filter]").forEach((button) => button.addEventListener("click", () => {
		attendanceFilter = button.dataset.attendanceFilter;
		document.querySelectorAll("[data-attendance-filter]").forEach((item) => item.classList.toggle("active", item === button));
		renderAttendanceHistory();
	}));
	document.querySelectorAll(".bottom-tabs [data-tab]").forEach((tab) => tab.addEventListener("click", () => showSection(tab.dataset.tab)));
	let swipeStart = null;
	byId("attendance-view").closest(".attendance-shell").addEventListener("touchstart", (event) => {
		if (event.touches.length !== 1 || !byId("notification-sheet").classList.contains("is-hidden") || !byId("leave-sheet").classList.contains("is-hidden") || !byId("leave-detail-sheet").classList.contains("is-hidden") || !byId("attendance-detail-sheet").classList.contains("is-hidden") || !byId("correction-sheet").classList.contains("is-hidden") || !byId("correction-detail-sheet").classList.contains("is-hidden") || !byId("app-dialog").classList.contains("is-hidden")) return;
		swipeStart = {x: event.touches[0].clientX, y: event.touches[0].clientY};
	}, {passive: true});
	byId("attendance-view").closest(".attendance-shell").addEventListener("touchend", (event) => {
		if (!swipeStart || !event.changedTouches.length) return;
		const dx = event.changedTouches[0].clientX - swipeStart.x;
		const dy = event.changedTouches[0].clientY - swipeStart.y;
		swipeStart = null;
		if (Math.abs(dx) < 55 || Math.abs(dx) < Math.abs(dy) * 1.25) return;
		const visibleTabs = tabOrder.filter((name) => !document.querySelector(`.bottom-tabs [data-tab="${name}"]`)?.hidden);
		const index = visibleTabs.indexOf(activeSection);
		const next = dx < 0 ? visibleTabs[index + 1] : visibleTabs[index - 1];
		if (next) showSection(next, dx < 0 ? "next" : "prev");
	}, {passive: true});
	byId("leave-balance-card").addEventListener("toggle", (event) => { if (event.target.open) loadLeaves(); });
	byId("open-leave-request").onclick = openLeaveRequest;
	byId("leave-sheet-close").onclick = closeLeaveRequest;
	byId("leave-sheet").addEventListener("click", (event) => { if (event.target === byId("leave-sheet")) closeLeaveRequest(); });
	byId("leave-from-date").addEventListener("change", () => { if (!byId("leave-to-date").value || byId("leave-to-date").value < byId("leave-from-date").value) byId("leave-to-date").value = byId("leave-from-date").value; byId("leave-to-date").min = byId("leave-from-date").value; });
	byId("leave-from-date").addEventListener("change", scheduleLeavePreview);
	byId("leave-to-date").addEventListener("change", () => { loadAvailableLeaveTypes(); scheduleLeavePreview(); });
	byId("leave-from-date").addEventListener("change", loadAvailableLeaveTypes);
	byId("leave-type").addEventListener("change", updateSelectedLeaveType);
	byId("leave-duration").addEventListener("change", updateHourlyFields);
	byId("leave-partial-hours").addEventListener("input", scheduleLeavePreview);
	byId("simple-leave-form").addEventListener("submit", submitSimpleLeave);
	["attendance-from", "attendance-to", "leave-from-date", "leave-to-date"].forEach((id) => autoCommitDatePicker(byId(id)));
	byId("logout-button").addEventListener("click", async (event) => {
		event.preventDefault();
		const confirmed = await showAppDialog({title: __("Log out?"), message: __("Are you sure you want to log out of the Employee HR Portal?"), icon: "↪", confirmLabel: __("Log Out"), showCancel: true, danger: true});
		if (!confirmed) return;
		frappe.call({method: "logout", type: "POST", callback: () => { localStorage.removeItem("hr_attendance_logged_in"); location.replace(`/attendance?logout=${Date.now()}`); }});
	});
	byId("action").onclick = async () => {
		if (busy) return;
		if (status?.require_geolocation && (!coords || coords.accuracy > status.maximum_gps_accuracy)) {
			feedback(__("Getting the required GPS accuracy…"));
			await locate(true);
		}
		if (status?.require_geolocation && !coords) return;
		busy = true; byId("action").disabled = true; setText("action-label", __("VALIDATING…"));
		feedback(__("Checking GPS and branch geofence…"));
		try {
			const response = await api("hr_custom.api.attendance_clock_v3.submit_checkin", {latitude: coords?.latitude, longitude: coords?.longitude, accuracy: coords?.accuracy, device_info: navigator.platform, device_id: deviceId});
			if (!response?.ok) throw new Error(response?.message || __("Could not record attendance"));
			const result = response.result;
			feedback("");
			historyLoaded = false;
			await refresh(false);
		} catch (error) {
			feedback("");
			byId("action").disabled = false;
			setText("action-label", status?.next_action === "IN" ? __("CLOCK IN") : __("CLOCK OUT"));
			const text = String(error?.message || __("Request failed."));
			const match = text.match(/You are\s+([\d,.]+)\s+meters away from\s+(?:the nearest allowed branch\s*\()?([^).]+)\)?\.\s*The allowed attendance radius is\s+([\d,.]+)\s+meters\.?/i);
			if (match) {
				const distance = Number(match[1].replaceAll(",", ""));
				const radius = Number(match[3].replaceAll(",", ""));
				const formatDistance = (meters) => meters >= 1000 ? `${(meters / 1000).toFixed(meters >= 10000 ? 0 : 1)} km` : `${Math.round(meters)} m`;
				await showAppDialog({
					title: __("Outside the allowed work location"),
					message: __("You are currently about {0} from {1}.\n\nTo record attendance, move within {2} of this branch, then try again.", [formatDistance(distance), match[2].trim(), formatDistance(radius)]),
					icon: "⌖", confirmLabel: __("Got it"), tone: "warning",
				});
			} else {
				await showAppDialog({title: __("Could not record attendance"), message: text, icon: "!", confirmLabel: __("Got it"), tone: "warning"});
			}
		} finally {
			busy = false;
			byId("action").disabled = false;
			setText("action-label", status?.next_action === "IN" ? __("CLOCK IN") : __("CLOCK OUT"));
		}
	};

	const installButtons = [byId("install-button"), byId("install-icon-button")].filter(Boolean);
	const setInstallButtonsHidden = (hidden) => installButtons.forEach((button) => button.classList.toggle("is-hidden", hidden));
	window.addEventListener("beforeinstallprompt", (event) => { event.preventDefault(); deferredInstall = event; setInstallButtonsHidden(false); });
	const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
	setInstallButtonsHidden(Boolean(standalone));
	const requestInstall = async () => {
		if (deferredInstall) { deferredInstall.prompt(); await deferredInstall.userChoice; deferredInstall = null; setInstallButtonsHidden(true); }
		else if (/iphone|ipad|ipod/i.test(navigator.userAgent)) openSheet(byId("ios-install-sheet"));
		else feedback(__("Use your browser menu and select Install app or Add to Home screen."));
	};
	installButtons.forEach((button) => { button.onclick = requestInstall; });
	byId("sheet-close").onclick = () => closeSheet(byId("ios-install-sheet"));
	const requestBackgroundRefresh = () => {
		clearTimeout(backgroundRefreshTimer);
		backgroundRefreshTimer = setTimeout(() => {
			if (document.visibilityState === "visible" && !overlayIsOpen() && !busy) refreshApp({background: true});
		}, 350);
	};
	setInterval(requestBackgroundRefresh, 30000);
	document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") requestBackgroundRefresh(); });
	window.addEventListener("focus", requestBackgroundRefresh);
	window.addEventListener("online", requestBackgroundRefresh);
	if (frappe.realtime?.on) frappe.realtime.on("notification", requestBackgroundRefresh);
	if ("serviceWorker" in navigator && window.isSecureContext) {
		navigator.serviceWorker.getRegistrations().then(async (registrations) => {
			for (const registration of registrations) {
				const script = registration.active?.scriptURL || registration.waiting?.scriptURL || registration.installing?.scriptURL || "";
				if (script.endsWith("/attendance-sw.js") && registration.scope === `${location.origin}/`) await registration.unregister();
			}
			await navigator.serviceWorker.register("/attendance-sw.js", {scope: "/attendance"});
		}).catch(() => {});
	}
	byId("attendance-to").value = moment().format("YYYY-MM-DD");
	byId("attendance-from").value = moment().startOf("month").format("YYYY-MM-DD");
	locate(false);
	refresh(false);
	loadNotifications();
	loadApprovals(true);
});
