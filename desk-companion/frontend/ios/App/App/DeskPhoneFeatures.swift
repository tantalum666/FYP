import Foundation
import UserNotifications
import WidgetKit
import Capacitor

let deskAppGroup = "group.dev.group2.deskcompanion"

enum DeskPhoneFeatures {
    static func clear() {
        UserDefaults(suiteName: deskAppGroup)?.removeObject(forKey: "calendar.snapshot")
        WidgetCenter.shared.reloadAllTimelines()
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
        UNUserNotificationCenter.current().removeAllDeliveredNotifications()
    }
    static func status(_ callback: @escaping ([String: Any]) -> Void) {
        let centre = UNUserNotificationCenter.current()
        centre.getNotificationSettings { settings in
            centre.getPendingNotificationRequests { requests in
                let status: String
                switch settings.authorizationStatus {
                case .authorized, .provisional, .ephemeral: status = "allowed"
                case .denied: status = "denied"
                default: status = "not_requested"
                }
                callback(["permission": status, "enabled": UserDefaults.standard.bool(forKey: "desk.notifications.enabled"), "scheduled": requests.count, "widgetAvailable": FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: deskAppGroup) != nil])
            }
        }
    }
    static func sync(_ supplied: [String: Any], completion: @escaping ([String: Any]) -> Void) {
        var snapshot = supplied
        let chinese = snapshot["language"] as? String == "zh"
        let items = (snapshot["items"] as? [[String: Any]] ?? []).prefix(3).map { row -> [String: Any] in
            var result = row
            if row["redacted"] as? Bool != false { result["title"] = "" }
            return result
        }
        snapshot["items"] = items
        snapshot.removeValue(forKey: "notifications")
        if let data = try? JSONSerialization.data(withJSONObject: snapshot), data.count < 30_000 {
            UserDefaults(suiteName: deskAppGroup)?.set(data, forKey: "calendar.snapshot")
            WidgetCenter.shared.reloadAllTimelines()
        }
        let centre = UNUserNotificationCenter.current()
        guard UserDefaults.standard.bool(forKey: "desk.notifications.enabled") else { centre.removeAllPendingNotificationRequests(); status(completion); return }
        centre.getNotificationSettings { settings in
            guard [.authorized, .provisional, .ephemeral].contains(settings.authorizationStatus) else { status(completion); return }
            let rows = (supplied["notifications"] as? [[String: Any]] ?? []).prefix(64)
            let formatter = ISO8601DateFormatter(); formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            // Replace the local cache on each explicit sync. It cannot reflect edits
            // made while this phone is offline; the notification says to check the app.
            centre.removeAllPendingNotificationRequests()
            let group = DispatchGroup()
            for row in rows {
                guard let id = row["id"] as? String, id.count <= 64, let at = row["at"] as? String, let when = formatter.date(from: at), when.timeIntervalSinceNow > 2, when.timeIntervalSinceNow < 7 * 86400 else { continue }
                let content = UNMutableNotificationContent()
                let title = row["title"] as? String ?? ""
                content.title = row["redacted"] as? Bool != false || title.isEmpty ? (chinese ? "私人日程" : "Private event") : String(title.prefix(160))
                content.body = chinese ? "已同步的日程提醒，打开App核对最新安排。" : "A synced calendar reminder. Open the app to check the latest schedule."
                if row["sound"] as? Bool == true { content.sound = .default }
                let request = UNNotificationRequest(identifier: "desk." + id, content: content, trigger: UNTimeIntervalNotificationTrigger(timeInterval: max(2, when.timeIntervalSinceNow), repeats: false))
                group.enter(); centre.add(request) { _ in group.leave() }
            }
            group.notify(queue: .main) { status(completion) }
        }
    }
}

extension DeskNativePlugin {
    @objc func phoneStatus(_ call: CAPPluginCall) { DeskPhoneFeatures.status { call.resolve($0) } }
    @objc func enableNotifications(_ call: CAPPluginCall) {
        if call.getBool("enabled") == false {
            UserDefaults.standard.set(false, forKey: "desk.notifications.enabled")
            UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
            DeskPhoneFeatures.status { call.resolve($0) }; return
        }
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { granted, error in
            if error != nil { call.reject("Notification permission could not be checked"); return }
            UserDefaults.standard.set(granted, forKey: "desk.notifications.enabled")
            DeskPhoneFeatures.status { call.resolve($0) }
        }
    }
    @objc func syncPhone(_ call: CAPPluginCall) {
        guard let object = call.getObject("snapshot") else { call.reject("Missing calendar snapshot"); return }
        DeskPhoneFeatures.sync(object) { call.resolve($0) }
    }
    @objc func clearPhone(_ call: CAPPluginCall) { DeskPhoneFeatures.clear(); call.resolve() }
}
