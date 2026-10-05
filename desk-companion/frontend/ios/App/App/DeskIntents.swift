import AppIntents
import Foundation

@MainActor
final class DeskRoute {
    static func request(_ route: String) {
        guard ["today", "new"].contains(route) else { return }
        UserDefaults.standard.set(route, forKey: "desk.pending.route.v1")
        NotificationCenter.default.post(name: Notification.Name("DeskRouteRequested"), object: nil)
    }
    static func receive(_ url: URL) {
        guard url.scheme == "deskcompanion" else { return }
        request(url.host == "new" ? "new" : "today")
    }
}
struct OpenDeskToday: AppIntent {
    static let title: LocalizedStringResource = "Open today’s calendar"
    static let openAppWhenRun = true
    func perform() async throws -> some IntentResult {
        await DeskRoute.request("today")
        return .result()
    }
}
struct ComposeDeskEvent: AppIntent {
    static let title: LocalizedStringResource = "Prepare a calendar event"
    static let openAppWhenRun = true
    func perform() async throws -> some IntentResult {
        await DeskRoute.request("new")
        return .result()
    }
}
struct DeskShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: OpenDeskToday(), phrases: ["Open today in \(.applicationName)"], shortTitle: "Today", systemImageName: "calendar")
        AppShortcut(intent: ComposeDeskEvent(), phrases: ["Add an event in \(.applicationName)"], shortTitle: "New event", systemImageName: "calendar.badge.plus")
    }
}
